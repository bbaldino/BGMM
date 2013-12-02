import json, os, errno

def read_config(config_file):
    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except IOError as e:
        pass
    return {}

def write_config(config, config_file):
    make_sure_path_exists(os.path.dirname(config_file))
    with open(config_file, "w+") as f:
        json.dump(config, f)

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else:
            return False

    return True
