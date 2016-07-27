#!/usr/bin/python
'''
Example run:
python socrates_cli.py --param param.json
'''
from bson.json_util import dumps
from bson import objectid
from bson.objectid import ObjectId
from datetime import datetime
from flask import Flask
from flask import render_template
from flask import request
from pprint import pprint
from pymongo import MongoClient
from translation import *
import argparse
import json
import modules
import sys
import traceback
import user

def _err(msg):
    return json.dumps({
    'error' : 'true',
    'message': msg
    })


def _parseCSV(csv_str):
    rows = csv_str.split('\n')
    keys = rows[0].split(",")
    working_set = {
        "meta" : {},
        "data" : []
    }
    for k in keys:
        working_set["meta"][k] = "text" #for now, assume text field
    for r in rows[1:]:
        row_obj = {}
        row_parts = r.split(",")
        for i in range(len(row_parts)):
            row_obj[keys[i]] = row_parts[i]
        working_set["data"].append(row_obj)
    return working_set

'''
The run method ties together the running of operators.
It will run the operator, store results, and return appropriate data to be sent back to user.
It will store/retrieve stored collection data
'''
def run(typ, mod, fn, param, working_set=None):
<<<<<<< Updated upstream
    is_new = False
    if typ in MODULE_LIST and mod in MODULE_LIST[typ]:
=======
  is_new = False
  op_set = make_operator_set (typ, mod, fn, param)
  workflow_id = addWorkflow(op_set)
  if typ in MODULE_LIST and mod in MODULE_LIST[typ]:
>>>>>>> Stashed changes
        #get module/function references
        callingTyp = getattr(modules, typ)
        callingMod = getattr(callingTyp, mod)
        callingFn = getattr(callingMod, fn)
        fn_specs = callingMod.SPECS['functions']
        #validate parameters from constraints
        if enforceAndConvert(param, fn_specs[fn]['param'], working_set) is False:
            return _err("Parameters are not valid") #get better error from constraint function

        applyDefaults(param, fn_specs[fn]['param'])
            
        #call and augment with meta information
        if typ == 'analysis':
            if working_set is None:
                return _err("Data not provided")
            is_new = False
            results = callingFn(working_set, param)
            if 'aggregate_result' in fn_specs[fn]:
                results['aggregate_meta'] = fn_specs[fn]['aggregate_result']
            if 'entry_result' in fn_specs[fn]:
                results['entry_meta'] = fn_specs[fn]['entry_result']
            if 'analysis' in working_set:
                working_set['analysis'].append(results)
            else:
                working_set['analysis'] = [results]
        elif typ == 'collection':
            is_new = True
            data = callingFn(param)
            working_set = {
                'data' : data, #only if specified
                'meta' : fn_specs[fn]['returns'],
                'input' : param
                }
        return (working_set, is_new)
    return (None, False)

def parse_params(parameters, ip=False):
    try:
        client = MongoClient()
        mongodb = client.socrates

        result = "{}" #string result from each run-type to print at the end
        working_set = None
        working_set_id = -1
        working_set_name = "Untitled"

        if 'username' in parameters and 'password' in parameters:
            if 'register' in parameters:
                #register new user
                taken = not user.register(parameters['username'], parameters['password'])
                result = json.dumps({"attempted": True, "taken" : taken})
            else:
                #authenticate
                if not user.authenticate(parameters['username'], parameters['password']):
                    return _err("Invalid username and password")
        else:
            #use default user
            user.setDefault()

        if 'working_set_id' in parameters:
            working_set_id = parameters['working_set_id']
            working_set = user.getWorkingSet(working_set_id)
            working_set_name = working_set["working_set_name"]

        if 'working_set_name' in parameters:
            working_set_name = parameters['working_set_name']

        #mutually exclusive if-elif
        if 'module' in parameters:
            typ = parameters['type']
            mod = parameters['module']
            fn = parameters['function']

            print "Running %s, %s, %s\n" % (typ, mod, fn)
            param = {}
            if "input" in parameters:
                param = parameters["input"]
            return_all_data = False
            if "return_all_data" in parameters:
                return_all_data = parameters["return_all_data"]

            if typ == "analysis" and working_set is None:
                return _err("Working set id not included")

            (working_set, is_new) = run(typ, mod, fn, param, working_set)

            user.log_run(typ, mod, fn)
            if ip:
                user.log_activity("run_ip", ip)

            if working_set is None:
                return _err("Internal operation error")
            if 'error' in working_set and working_set['error']:
                return _err("error: " + working_set['message'])

            #store new/modified working set
            working_set["working_set_name"] = working_set_name
            if is_new:
                insert_id = user.addWorkingSet(working_set)
                #user.test(working_set)
                working_set['working_set_id'] = str(insert_id)
            else:
                user.updateWorkingSet(working_set_id, working_set) #overwrite in database
                working_set['working_set_id'] = str(working_set_id)

            if not return_all_data:
                #remove all data except first entry
                working_set["data"] = working_set["data"][0:1]
                if "analysis" in working_set:
                    for i in range(len(working_set["analysis"])):
                        a = working_set["analysis"][i]
                        if "entry_analysis" in a:
                            for p in a['entry_analysis']:
                                a['entry_analysis'][p] = a['entry_analysis'][p][0:1]

            return dumps(working_set)

        elif 'specs' in parameters:
            print "Fetching specs\n"
            if ip:
                user.log_activity("fetch_ip", ip)
            return json.dumps(getAllSpecs())

        elif 'fetch' in parameters:
            working_set = user.getWorkingSet(working_set_id)
            working_set['working_set_id'] = str(working_set_id)
            return dumps(working_set)

        elif 'remove' in parameters:
            user.removeWorkingSet(working_set_id)
            return dumps({"status" : "success"})

        elif 'rename' in parameters:
            user.renameWorkingSet(working_set_id, parameters['new_name'])
            return dumps({"status" : "success"})

        elif 'fetch_all_ids' in parameters:
            working_sets = user.getWorkingSets()
            working_set_identifiers = []
            for w in working_sets:
                wid = {
                    "id" : w["working_set_id"],
                    "name" : "Untitled"
                }
                if "working_set_name" in w:
                    wid["name"] = w["working_set_name"]

                working_set_identifiers.append(wid)

            return dumps({
                "ids" : working_set_identifiers
                })
            
        elif 'upload' in parameters:
            working_set = None
            default_working_set_name = "Imported Dataset"
            data = parameters['working_set_data']
            format = parameters['format']
            if format not in ["csv", "json"]:
                return _err("Invalid upload format selected")
            if format == "json":
                try:
                    working_set = json.loads(data) #no additional parsing necessary
                except ValueError as ve:
                    return _err("Working set JSON could not be parsed")
            elif format == "csv":
                #parse string as csv
                working_set = _parseCSV(data)

            if working_set is not None:
                if "working_set_name" not in working_set:
                    working_set["working_set_name"] = default_working_set_name
                working_set_id = user.addWorkingSet(working_set)
                return dumps({
                    "id" : str(working_set_id),
                    "name" : working_set["working_set_name"]
                    })

            else:
                return _err("Could not upload")
        return result

    except Exception as e:
        sys.stderr.write("Exception caught: %s\n" % e)
        sys.stderr.write("Stack trace:\n%s\n" % traceback.format_exc())

app = Flask(__name__)
@app.route("/socrates", methods=["POST"])
def endpoint():
    params = request.get_json(silent=True)
    if not params:
        return _err("Cannot parse JSON request")
    return parse_params(params, False)

@app.route("/one", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # A key error generates an HTTP 400 bad request
        # which is appropriate if username/password are missing
        username = request.form['username']
        password = request.form['password']
        return render_template('index.html', username=username, password=password)
    else:
        return render_template('index.html')

@app.route("/app", methods=['GET', 'POST'])
@app.route("/two", methods=['GET', 'POST'])
def two():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        return render_template('socrates2.html', username=username, password=password)
    else:
        return render_template('socrates2.html')

@app.route("/form", methods=['GET'])
def form():
    return app.send_static_file('test-form.html')

@app.route("/", methods=['GET'])
def homepage():
    return app.send_static_file('landing/index.html')

def init():
    parser = argparse.ArgumentParser(description="SOCRATES Social media data collection, analysis, and exploration")
    parser.add_argument("--param", help="use parameter file for input", default=False)
    parser.add_argument("--fileout", help="put output in specified file", default=False)
    parser.add_argument("--ip", help="stores IP address", default=False)
    parser.add_argument("--serve", help="start web server", action="store_true")
    args = parser.parse_args()

    parameters = None
    if args.param:
        param_file = open(args.param, "r")
        parameters = json.load(param_file)
        param_file.close()
        result = parse_params(parameters, args.ip)
        if args.fileout:
            out_file = open(args.fileout, 'w')
            out_file.write(result)
            out_file.close()
            print "Results written to file %s" % args.fileout
        else:
            print result
    elif args.serve:
        app.run(debug=True)
        return
    else:
        parser.print_help() 

init()