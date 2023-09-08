import subprocess
import os
import sys
import importlib.util
import shlex
import platform
import json
from pathlib import Path

import argparse


commandline_args = os.environ.get('COMMANDLINE_ARGS', "")


# 打印参数值
print("args:", commandline_args)



python = sys.executable
git = os.environ.get('GIT', "git")
index_url = os.environ.get('INDEX_URL', "")
stored_commit_hash = None
skip_install = False
dir_repos = "repositories"

def is_installed(package):
    try:
        spec = importlib.util.find_spec(package)
    except ModuleNotFoundError:
        return False

    return spec is not None


def check_python_version():
    is_windows = platform.system() == "Windows"
    major = sys.version_info.major
    minor = sys.version_info.minor
    micro = sys.version_info.micro

    if is_windows:
        supported_minors = [10]
    else:
        supported_minors = [8, 9, 10]

    if not (major == 3 and minor in supported_minors):
        print(f"""
PYTHON 版本不匹配
你的 PYTHON 版本： {major}.{minor}.{micro}
本程序在 PYTHON 3.10 完成测试.
""")

def run(command, desc=None, errdesc=None, custom_env=None, live=False):
    if desc is not None:
        print(desc)

    if live:
        result = subprocess.run(command, shell=True, env=os.environ if custom_env is None else custom_env)
        if result.returncode != 0:
            raise RuntimeError(f"""{errdesc or 'Error running command'}.
Command: {command}
Error code: {result.returncode}""")

        return ""

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=os.environ if custom_env is None else custom_env)

    if result.returncode != 0:

        message = f"""{errdesc or 'Error running command'}.
Command: {command}
Error code: {result.returncode}
stdout: {result.stdout.decode(encoding="utf8", errors="ignore") if len(result.stdout)>0 else '<empty>'}
stderr: {result.stderr.decode(encoding="utf8", errors="ignore") if len(result.stderr)>0 else '<empty>'}
"""
        raise RuntimeError(message)

    return result.stdout.decode(encoding="utf8", errors="ignore")

def commit_hash():
    global stored_commit_hash

    if stored_commit_hash is not None:
        return stored_commit_hash

    try:
        stored_commit_hash = run(f"{git} rev-parse HEAD").strip()
    except Exception:
        stored_commit_hash = "<none>"

    return stored_commit_hash

def run_pip(args, desc=None):
    if skip_install:
        return

    index_url_line = f' --index-url {index_url}' if index_url != '' else ''
    return run(f'"{python}" -m pip {args} --prefer-binary{index_url_line}', desc=f"Installing {desc}", errdesc=f"Couldn't install {desc}")



def prepare_environment():
    global skip_install

    torch_command = os.environ.get('TORCH_COMMAND', "pip install torch==1.13.1+cu117 torchvision==0.14.1+cu117 --extra-index-url https://download.pytorch.org/whl/cu117")
    # requirements_file = os.environ.get('REQS_FILE', "requirements.txt")

    # 安装torch GPU版本
    if not is_installed("torch") or not is_installed("torchvision"):
        run(f'"{python}" -m {torch_command}', "Installing torch and torchvision", "Couldn't install torch", live=True)
        
    if not is_installed("transformers"):
        run_pip(f"install git+https://ghproxy.com/https://github.com/huggingface/transformers.git -i https://pypi.tuna.tsinghua.edu.cn/simple","transformers")
    
    if not is_installed("pydub"):
        run_pip(f"install pydub -i https://pypi.tuna.tsinghua.edu.cn/simple","pydub")

    if not is_installed("scipy"):
        run_pip(f"install scipy -i https://pypi.tuna.tsinghua.edu.cn/simple","scipy")
  
    if not is_installed('flask'):
        run_pip(f"install Flask -i https://pypi.tuna.tsinghua.edu.cn/simple", "Flask")

    if not is_installed("flask_cors"):
        run_pip(f"install Flask-Cors -i https://pypi.tuna.tsinghua.edu.cn/simple","Flask-Cors")

    check_python_version()

    commit = commit_hash()

    print(f"Python {sys.version}")
    print(f"Commit hash: {commit}")

    print(platform.system(),platform.python_version().startswith("3.10"))
    


def start():
    os.system(f'"{python}" server/server.py')


if __name__ == "__main__":
    prepare_environment()
    start()
