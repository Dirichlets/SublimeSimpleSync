#
# Sublime Text 2/3 SimpleSync plugin
#
# based on https://github.com/tnhu/SimpleSync
#

import os, sys, platform
import subprocess
import threading
import re
import sublime, sublime_plugin
print(os.path.join(sublime.packages_path(), 'Default'))
# Caches
PACKAGE_NAME = 'SublimeSimpleSync' #__name__ # ST3 bug with __name__
PACKAGE_SETTINGS = PACKAGE_NAME + '.sublime-settings'
OS = platform.system()
# print('*********', os.name, sys.platform, OS)
IS_GTE_ST3 = int(sublime.version()[0]) >= 3

class syncCommand():

    # get settings
    def getSetting(self):
        return sublime.load_settings(PACKAGE_SETTINGS)

    # Get file path
    def getPath(self):
        if self.window.active_view():
            return self.window.active_view().file_name()
        else:
            sublime.error_message(PACKAGE_NAME + ': No file_name')
            return False

    # Get sync item(s) for a file
    def getSyncItem(self, localFile, rules):
        ret = []
        # print(localFile, rules)
        for item in rules:
            # print(item)
            if localFile.startswith(item['local']):
                ret += [item]
        return ret

    # support multiple rules
    def syncFile(self, localFile, rules):
        syncItems = self.getSyncItem(localFile, rules)
        # print('+++ syncCommand: ', syncItems)
        if (len(syncItems) > 0):
            for item in syncItems:
                # fix path(/)
                # remoteFile = localFile.replace(item['local'], item['remote'] + '/')
                relPath = localFile.replace(item['local'], '')
                remoteFile = item['remote'] + '/' + relPath;
                # print('********', remoteFile)
                if (item['type'] == 'ssh'):
                    password = item['password'] if 'password' in item else ''
                    ScpCopier(item['host'], item['username'], password, localFile, remoteFile, port=item['port'], relPath=relPath).start()
                elif (item['type'] == 'local'):
                    # self.localCopier(localFile, remoteFile)
                    LocalCopier(localFile, remoteFile).start()

# { "keys": ["alt+s"], "command": "simple_sync"},
class SublimeSimpleSyncCommand(sublime_plugin.WindowCommand, syncCommand):
    def run(self):
        settings = self.getSetting()
        rules = settings.get('rules')
        # auto save
        self.window.run_command('save')

        localFile = self.getPath()
        # print('********', localFile)
        self.syncFile(localFile, rules)

# auto run, sublime_plugin.EventListener
class SimpleSync(sublime_plugin.EventListener, syncCommand):  
    # on save
    def on_post_save(self, view):
        settings = self.getSetting()
        # print('********', settings)

        config = settings.get('config', [])
        autoSycn = config['autoSync'] if 'autoSync' in config else False
        localFile =  view.file_name() # self.getPath() # 'SimpleSync' object has no attribute 'window'
        # print('********', localFile)

        if autoSycn:
            rules = settings.get('rules')
            self.syncFile(localFile, rules)

# ScpCopier does actual copying using threading to avoid UI blocking
class ScpCopier(threading.Thread, syncCommand):
    def __init__(self, host, username, password, localFile, remoteFile, port=22, relPath=''):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.localFile = localFile
        self.remoteFile = remoteFile
        self.relPath = relPath
        # print('relative path:', relPath)

        settings = self.getSetting()
        config = settings.get('config')
        self.debug = config['debug'] if 'debug' in config else False

        threading.Thread.__init__(self)

    def run(self):
        packageDir = os.path.join(sublime.packages_path(), PACKAGE_NAME)
        # for windows
        self.remoteFile = self.remoteFile.replace('\\', '/').replace('//', '/')
        remote  = self.username + '@' + self.host + ':' + self.remoteFile

        # print('SimpleSync: ', self.localFile, ' -> ', self.remoteFile)

        pw = []
        if self.password:
            pw = ['-pw', self.password]

        ext = ['-r', '-C', '-P', str(self.port), self.localFile, remote]

        if OS == 'Windows':
            # cmd = os.environ['SYSTEMROOT'] + '\\System32\\cmd.exe'

            scp = os.path.join(packageDir, 'pscp.exe')
            args = [scp]
                # args = [scp, "-v"] # show message

            # run with .bat
            # scp = os.path.join(packageDir, 'sync.bat')
            # args = [scp]
            # pw.extend(ext)
            # pw = ' '.join(pw)
            # args.extend([packageDir, pw])
        else:
            args = ['scp']

        args.extend(pw)
        args.extend(ext)
        print('SimpleSync: ', ' '.join(args))

        # return
        try:
            if self.debug:
                # for console.log
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                result = ''
                def syncFolder():
                    self.localFile = os.path.dirname(self.localFile)
                    self.remoteFile = os.path.dirname(os.path.dirname(self.remoteFile))
                    # print(self.localFile, ',', self.remoteFile)
                    ScpCopier(self.host, self.username, self.password, self.localFile, self.remoteFile, self.port).start()

                def showMsg(msg):
                    error_msg = 'no such file or directory'
                    m = re.search(error_msg, msg)
                    if m is not None: # do something
                        if sublime.ok_cancel_dialog(error_msg + '\r\n' + self.relPath + '\r\n' +'* Are you want to sync parent folder?'):
                            syncFolder()
                    else:
                        # sublime.status_message(msg)
                        sublime.message_dialog(msg)

                result = p.stdout.read().decode('utf-8');
                #     if IS_GTE_ST3:
                #         buff = buff.decode('utf-8')
                # print(result)
                showMsg(result)
            else:
                retcode = subprocess.call(args)
                print(retcode)
                if retcode != 0: # error
                    sublime.message_dialog('sync failed')

        except Exception as exception:
            # Alert "SimpleSync: No file_name", if the file size is zero.
            # print(exception);
            sublime.error_message(PACKAGE_NAME + ': ' + exception)

# LocalCopier does local copying using threading to avoid UI blocking
class LocalCopier(threading.Thread, syncCommand):
  def __init__(self, localFile, remoteFile):
    self.localFile  = localFile
    self.remoteFile = remoteFile

    # settings = self.getSetting()
    # config = settings.get("config")
    # self.debug = config['debug'] if "debug" in config else False

    threading.Thread.__init__(self)

  def run(self):
    # print('SimpleSync: ', self.localFile, ' -> ', self.remoteFile)

    if OS == 'Windows':
        # subprocess.call(args)
        # cmd = os.environ['SYSTEMROOT'] + '\\System32\\cmd.exe'
        # args = [cmd, '/c', 'copy', '/y']

        # subprocess.call(args, shell=True)
        # args = ['copy', '/y']
        args = ['xcopy', '/y', '/e', '/h']

        # folder path
        # print(os.path.split(self.remoteFile)[0])
        # print(os.path.dirname(self.remoteFile))
        # print(re.sub(r'\\[^\\]*$', '', self.remoteFile))

        # print('*********', self.remoteFile)
        # replace C:\test/\test\ -> C:\test\test\
        self.remoteFile = self.remoteFile.replace('/\\', '\\')
        # replace /path/file.ext -> /path
        self.remoteFile = os.path.dirname(self.remoteFile) + '\\'
        # print('*********', self.remoteFile)
    else:
        args = ['cp']
    args.extend([self.localFile, self.remoteFile])

    print('SimpleSync: ', ' '.join(args))
    # return
    try:
        retcode = subprocess.call(args, shell=True) 
            # print(retcode) 

    except Exception as exception:
        # print(exception);
        sublime.error_message(PACKAGE_NAME + ': ' + str(exception))
