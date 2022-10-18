#!/usr/bin/env python3

import os
import subprocess
import shutil

def run(cmd, helper=None):
    print("$ " + cmd)
    if helper is None:
        subprocess.check_call(cmd, shell=True)
    else:
        helper()

if not os.path.isdir("node_modules"): run("npm install")
if os.path.isdir("src"): run("rm -rf src", lambda: shutil.rmtree("src"))
if os.path.isdir("dist"): run("rm -rf dist", lambda: shutil.rmtree("dist"))

run("mkdir src", lambda: os.mkdir("src"))
run("cp helper.js src/index.js", lambda: shutil.copy("helper.js", os.path.join("src", "index.js")))
run("npx webpack --mode=production")
run("cp dist/main.js cidr_helper.min.js", lambda: shutil.copy(os.path.join("dist", "main.js"), "cidr_helper.min.js"))
