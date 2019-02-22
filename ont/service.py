from flask import Flask, redirect, request, abort, render_template, session
from flask_cors import CORS
from flask_socketio import SocketIO
from ont.api import OntologyAPI

import json
import os


app = Flask(__name__, template_folder="../ui/templates/")
CORS(app)
socketio = SocketIO(app)

app.secret_key = "leia-ontology-service"


### /ontology/api - routes for query, returning JSON formatted results


@app.route("/ontology/api/get", methods=["GET"])
def api_get():
    if "concept" not in request.args:
        abort(400)

    concepts = request.args.getlist("concept")
    return json.dumps(OntologyAPI().get(concepts))


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


### /ontology/edit - routes for the editor and browser ui, both GET and PUT


@app.route("/ontology/edit/", methods=["GET"])
def edit():
    return redirect("/ontology/edit/all")


@app.route("/ontology/edit/<concept>", methods=["GET"])
def edit_concept(concept):
    if "recent" not in session:
        session["recent"] = list()

    results = OntologyAPI().get(concept, metadata=True)
    if len(results) != 1:
        session["not-found"] = concept
        redirect_url = session["recent"][-1] if len(session["recent"]) > 0 else "all"
        return redirect("/ontology/edit/" + redirect_url)

    definition = results[0][concept]
    parents = sorted(definition["is-a"]["value"])
    subclasses = sorted(OntologyAPI().descendants(concept, immediate=True))
    siblings = sorted(OntologyAPI().siblings(concept))
    properties = [] # TODO: OntologyAPI().format(definition)

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

    print(payload)

    return render_template("editor.html", payload=payload)


### /ontology/manage - routes for the version management system


@app.route("/ontology/manage", methods=["GET"])
def manage():

    message = request.args["message"] if "message" in request.args else None
    error = request.args["error"] if "error" in request.args else None

    from ont.management import active, list_collections, list_local_archives, list_remote_archives, ARCHIVE_PATH
    payload = {
        "active": active(),
        "installed": list_collections(),
        "local": list(list_local_archives()),
        "remote": list(list_remote_archives()),
        "local-volume": ARCHIVE_PATH,
        "message": message,
        "error": error
    }

    return render_template("manager.html", payload=payload)


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