from flask import Flask, jsonify, make_response, redirect, request, abort, render_template, session
from flask_cors import CORS
from flask_socketio import SocketIO
from itertools import groupby
from ont.api import OntologyAPI

import json
import ont.management
import os


app = Flask(__name__, template_folder="../ui/templates/")
CORS(app)
socketio = SocketIO(app)

app.secret_key = "leia-ontology-service"

EDITING_ENABLED = os.environ["EDITING_ENABLED"].lower() == "true" if "EDITING_ENABLED" in os.environ else True


def env_payload():
    if "recent-reports" not in session:
        session["recent-reports"] = list()

    if "editing" not in session:
        session["editing"] = False

    return {
        "editing_enabled": EDITING_ENABLED,
        "active_ontology": ont.management.active(),
        "editing": session["editing"] and EDITING_ENABLED,
        "recent-reports": session["recent-reports"],
    }


### /ontology/api - routes for query, returning JSON formatted results


@app.route("/ontology/api/get", methods=["GET"])
def api_get():
    if "concept" not in request.args:
        abort(400)

    local = False
    try:
        local = request.args.get("local").lower() == "true"
    except: pass

    concepts = request.args.getlist("concept")
    return json.dumps(OntologyAPI().get(concepts, local=local))


@app.route("/ontology/api/search", methods=["GET"])
def api_search():
    name_like = request.args.get("name_like")

    return json.dumps(OntologyAPI().search(name_like=name_like))


@app.route("/ontology/api/ancestors", methods=["GET"])
def api_ancestors():
    if "concept" not in request.args:
        abort(400)

    concept = request.args["concept"]
    immediate = False if "immediate" not in request.args else request.args["immediate"].lower() == "true"
    details = False if "details" not in request.args else request.args["details"].lower() == "true"
    paths = False if "paths" not in request.args else request.args["paths"].lower() == "true"

    return json.dumps(OntologyAPI().ancestors(concept, immediate=immediate, details=details, paths=paths))


@app.route("/ontology/api/descendants", methods=["GET"])
def api_descendants():
    if "concept" not in request.args:
        abort(400)

    concept = request.args["concept"]
    immediate = False if "immediate" not in request.args else request.args["immediate"].lower() == "true"
    details = False if "details" not in request.args else request.args["details"].lower() == "true"
    paths = False if "paths" not in request.args else request.args["paths"].lower() == "true"

    return json.dumps(OntologyAPI().descendants(concept, immediate=immediate, details=details, paths=paths))


@app.route("/ontology/api/inverses", methods=["GET"])
def api_inverses():
    return json.dumps(OntologyAPI().inverses())


@app.route("/ontology/api/relations", methods=["GET"])
def api_relations():
    inverses = False if "inverses" not in request.args else request.args["inverses"].lower() == "true"

    return json.dumps(OntologyAPI().relations(inverses=inverses))


### /ontology/view - routes for the editor and browser ui, GET only


@app.route("/ontology/view/", methods=["GET"])
def view():
    return redirect("/ontology/view/all")


@app.route("/ontology/view/<concept>", methods=["GET"])
def view_concept(concept):

    if ont.management.active() is None:
        return redirect("/ontology/manage")

    if not ont.management.can_connect():
        if "not-found" in session:
            session.pop("not-found")
        return redirect("/ontology/manage")

    if concept != concept.lower():
        return redirect("/ontology/view/" + concept.lower())

    if "recent" not in session:
        session["recent"] = list()

    if "editing" not in session:
        session["editing"] = False

    results = OntologyAPI().get(concept, metadata=True)
    if len(results) != 1:
        session["not-found"] = concept
        redirect_url = session["recent"][-1] if len(session["recent"]) > 0 else "all"
        return redirect("/ontology/view/" + redirect_url)

    definition = results[0][concept]
    parents = sorted(definition["is-a"]["value"])
    subclasses = sorted(OntologyAPI().descendants(concept, immediate=True))
    siblings = sorted(OntologyAPI().siblings(concept))

    properties = []
    for slot in results[0][concept]:
        if slot in ["is-a", "subclasses", "_metadata"]: continue
        for facet in results[0][concept][slot]:
            if facet in ["is_relation"]: continue
            for filler in results[0][concept][slot][facet]:
                filler["is_relation"] = results[0][concept][slot]["is_relation"]
                filler["from"] = None if concept == filler["defined_in"] else filler["defined_in"]
                filler["status"] = "local"
                if filler["blocked"]:
                    filler["status"] = "blocked"
                elif filler["from"] is not None:
                    filler["status"] = "inherit"

                properties.append(((slot, facet), filler))
    properties = groupby(properties, key=lambda p: p[0])
    properties = list(map(lambda p: (p[0], list(map(lambda f: f[1], p[1]))), properties))

    def determine_slot_facet_status(fillers):
        unique_filler_statuses = set(map(lambda f: f["status"], fillers))
        if "local" in unique_filler_statuses:
            return "local"
        if {"blocked"} == unique_filler_statuses:
            return "blocked"
        return "inherit"

    properties = list(map(lambda p: {"slot": p[0][0], "facet": p[0][1], "fillers": p[1], "status": determine_slot_facet_status(p[1])}, properties))
    properties = sorted(properties, key=lambda p: (p["slot"], p["facet"]))
    properties = list(properties)

    payload = {
        "name": concept,
        "metadata": definition["_metadata"],
        "isa": parents,
        "subclasses": subclasses,
        "siblings": siblings,
        "properties": properties,
        "recent": session["recent"]
    }

    if payload["name"] in session["recent"]:
        session["recent"].remove(payload["name"])
    session["recent"].append(payload["name"])
    session["recent"] = session["recent"][-10:]

    if "not-found" in session:
        payload["error-not-found"] = session["not-found"]
        session.pop("not-found")

    return render_template("editor.html", payload=payload, env=env_payload())


@app.route("/ontology/view/report/<concept>", methods=["GET"])
def view_report(concept):

    if ont.management.active() is None:
        return redirect("/ontology/manage")

    if not ont.management.can_connect():
        return redirect("/ontology/manage")

    if concept != concept.lower():
        return redirect("/ontology/view/report/" + concept.lower())

    usage_with_inheritance = False
    try:
        usage_with_inheritance = request.args.get("inh").lower() == "true"
    except: pass

    report = OntologyAPI().report(concept, include_usage=True, usage_with_inheritance=usage_with_inheritance)
    report["name"] = concept
    report["usage"]["inverses"] = sorted(report["usage"]["inverses"], key=lambda k: (k["concept"].lower(), k["slot"], k["facet"]))

    if "recent-reports" not in session:
        session["recent-reports"] = list()

    if concept in session["recent-reports"]:
        session["recent-reports"].remove(concept)
    session["recent-reports"].append(concept)
    session["recent-reports"] = session["recent-reports"][-10:]

    if "editing" not in session:
        session["editing"] = False

    return render_template("report.html", report=report, env=env_payload(), inh=usage_with_inheritance)


@app.route("/ontology/view/toggle/editing")
def view_toggle_editing():
    if "editing" not in session:
        session["editing"] = False

    session["editing"] = not session["editing"]

    return "OK"


### /ontology/edit - routes for the editor api, POST only


@app.route("/ontology/edit/define/<concept>", methods=["POST"])
def edit_define(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "definition" not in data:
        abort(400)

    OntologyAPI().update_definition(concept, data["definition"])

    return "OK"


@app.route("/ontology/edit/insert/<concept>", methods=["POST"])
def edit_insert(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "slot" not in data or "facet" not in data or "filler" not in data:
        abort(400)

    OntologyAPI().insert_property(concept, data["slot"], data["facet"], data["filler"])

    return "OK"


@app.route("/ontology/edit/remove/<concept>", methods=["POST"])
def edit_remove(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "slot" not in data or "facet" not in data or "filler" not in data:
        abort(400)

    OntologyAPI().remove_property(concept, data["slot"], data["facet"], data["filler"])

    return "OK"


@app.route("/ontology/edit/block/<concept>", methods=["POST"])
def edit_block(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "slot" not in data or "facet" not in data or "filler" not in data:
        abort(400)

    OntologyAPI().block_property(concept, data["slot"], data["facet"], data["filler"])

    return "OK"


@app.route("/ontology/edit/unblock/<concept>", methods=["POST"])
def edit_unblock(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "slot" not in data or "facet" not in data or "filler" not in data:
        abort(400)

    OntologyAPI().unblock_property(concept, data["slot"], data["facet"], data["filler"])

    return "OK"


@app.route("/ontology/edit/add_parent/<concept>", methods=["POST"])
def edit_add_parent(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "parent" not in data:
        abort(400)

    parent = data["parent"]

    if len(OntologyAPI().get(concept, local=True)) == 0:
        abort(make_response(jsonify(message="Unknown concept %s." % concept.lower()), 400))

    if len(OntologyAPI().get(parent, local=True)) == 0:
        abort(make_response(jsonify(message="Unknown concept %s." % parent.lower()), 400))

    OntologyAPI().add_parent(concept, parent)

    return "OK"


@app.route("/ontology/edit/remove_parent/<concept>", methods=["POST"])
def edit_remove_parent(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "parent" not in data:
        abort(400)

    OntologyAPI().remove_parent(concept, data["parent"])

    return "OK"


@app.route("/ontology/edit/add_concept", methods=["POST"])
def edit_add_concept():
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "concept" not in data or "parent" not in data or "definition" not in data:
        abort(400)

    parent = data["parent"]

    if len(OntologyAPI().get(parent, local=True)) == 0:
        abort(make_response(jsonify(message="Unknown concept %s." % parent.lower()), 400))

    OntologyAPI().add_concept(data["concept"], parent, data["definition"])

    return "OK"


@app.route("/ontology/edit/remove_concept/<concept>", methods=["POST"])
def edit_remove_concept(concept):
    if not EDITING_ENABLED:
        abort(403)

    if not request.get_json():
        abort(400)

    data = request.get_json()
    if "include_usages" not in data:
        abort(400)

    OntologyAPI().remove_concept(concept, include_usages=data["include_usages"])

    return "OK"


### /ontology/manage - routes for the version management system


@app.route("/ontology/manage", methods=["GET"])
def manage():

    message = request.args["message"] if "message" in request.args else None
    error = request.args["error"] if "error" in request.args else None

    from ont.management import active, compile_progress, list_collections, list_local_archives, list_remote_archives, ARCHIVE_PATH
    payload = {
        "active": active(),
        "installed": list_collections(),
        "local": list(list_local_archives()),
        "remote": list(list_remote_archives()),
        "local-volume": ARCHIVE_PATH,
        "message": message,
        "error": error,
        "compiled": compile_progress()
    }

    return render_template("manager.html", payload=payload, env=env_payload())


@app.route("/ontology/manage/activate", methods=["POST"])
def manage_activate():

    ontology = request.form["ontology"]

    try:
        from ont.management import activate
        activate(ontology)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    return redirect("/ontology/manage")


@app.route("/ontology/manage/copy", methods=["POST"])
def manage_copy():

    name = request.form["name"]
    ontology = request.form["ontology"]

    try:
        from ont.management import copy_collection
        copy_collection(ontology, name)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Copied " + ontology + " to " + name + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/rename", methods=["POST"])
def manage_rename():

    name = request.form["name"]
    ontology = request.form["ontology"]

    try:
        from ont.management import rename_collection
        rename_collection(ontology, name)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Renamed " + ontology + " to " + name + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/archive", methods=["POST"])
def manage_archive():

    name = request.form["name"]
    ontology = request.form["ontology"]

    filename = name + ".gz"

    try:
        from ont.management import collection_to_file, list_collections, rename_collection, ARCHIVE_PATH

        if name != ontology and name in list_collections():
            raise Exception("Cannot archive using another name that already exists.")

        path = os.environ[ARCHIVE_PATH] if ARCHIVE_PATH in os.environ else None

        if path is None:
            raise Exception("Unknown ARCHIVE_PATH variable.")

        if name != ontology:
            rename_collection(ontology, name)

        collection_to_file(name, path)

        if name != ontology:
            rename_collection(name, ontology)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Archived " + ontology + " to " + filename + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/compile", methods=["POST"])
def manage_compile():
    ontology = request.form["ontology"]
    compile_inherited_values = "inh" in request.form
    compile_domains_and_ranges = "dr" in request.form
    compile_inverses = "inv" in request.form

    from threading import Thread

    t = Thread(target=ont.management.compile, args=(ontology,), kwargs={
        "compile_inherited_values": compile_inherited_values,
        "compile_domains_and_ranges": compile_domains_and_ranges,
        "compile_inverses": compile_inverses,
    })
    t.start()

    message = "Compile started on " + ontology + "."
    return redirect("/ontology/manage?message=" + message)

@app.route("/ontology/manage/export", methods=["POST"])
def manage_export():
    ontology = request.form["ontology"]
    format = request.form["format"]

    file = ont.management.export(ontology, format)

    from flask import send_file
    return send_file(file, as_attachment=True)

@app.route("/ontology/manage/delete", methods=["POST"])
def manage_delete():

    ontology = request.form["ontology"]

    try:
        from ont.management import delete_collection
        delete_collection(ontology)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Deleted " + ontology + " from the database."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/local/install", methods=["POST"])
def manage_local_install():

    ontology = request.form["ontology"]

    try:
        from ont.management import file_to_collection, ARCHIVE_PATH
        path = os.environ[ARCHIVE_PATH] if ARCHIVE_PATH in os.environ else None

        if path is None:
            raise Exception("Unknown ARCHIVE_PATH variable.")

        path = path + "/" + ontology + ".gz"

        file_to_collection(path)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Installed " + ontology + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/local/publish", methods=["POST"])
def manage_local_publish():

    ontology = request.form["ontology"]

    try:
        from ont.management import publish_archive
        publish_archive(ontology)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Published " + ontology + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/local/delete", methods=["POST"])
def manage_local_delete():

    ontology = request.form["ontology"]

    try:
        from ont.management import delete_local_archive
        delete_local_archive(ontology)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Deleted archive " + ontology + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/remote/download", methods=["POST"])
def manage_remote_download():

    ontology = request.form["ontology"]

    try:
        from ont.management import download_archive
        download_archive(ontology)
    except Exception as e:
        return redirect("/ontology/manage?error=" + e.message)

    message = "Downloaded " + ontology + "."
    return redirect("/ontology/manage?message=" + message)


@app.route("/ontology/manage/new", methods=["POST"])
def manage_new():
    ontology = request.form["ontology"]

    from ont.management import make_collection
    make_collection(ontology)

    message = "Made and activated " + ontology + "."
    return redirect("/ontology/manage?message=" + message)


if __name__ == '__main__':
    host = "127.0.0.1"
    port = 5003

    import sys

    for arg in sys.argv:
        if '=' in arg:
            k = arg.split("=")[0]
            v = arg.split("=")[1]

            if k == "host":
                host = v
            if k == "port":
                port = int(v)

    socketio.run(app, host=host, port=port, debug=False)