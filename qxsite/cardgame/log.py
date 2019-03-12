from qxsite.settings import LOG_FILE

def log(*args):
    logfile = open(LOG_FILE, 'a')
    print(*args, file = logfile)
    logfile.close()