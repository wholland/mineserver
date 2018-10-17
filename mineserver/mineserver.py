import click
import os
import libtmux
import sys
import time
import subprocess

tmux = None

@click.group()
def cli():
    global tmux
    tmux = libtmux.Server()
    if not tmux:
        raise Exception('tmux server not found')

@cli.command(name='start')
@click.argument('nickname')
@click.argument('root', type=click.Path(exists=True))
@click.option('--sleep/--no-sleep', default=True)
def start_command(nickname, root, sleep):
    if not os.path.isfile(os.path.join(root, 'server.jar')):
        raise ValueError('Invalid root dir. Server file not found')

    server_cmd = 'cd {}; java -Xmx1024M -Xms1024M -d64 -jar server.jar'.format(root)
    click.echo(server_cmd)

    if sleep:
        click.echo('Starting server...', nl=False)

    res = tmux.cmd('new-session', '-d', '-s', nickname, server_cmd)
    if res.stderr:
        click.echo('Unable to start new session', err=True)
        for l in res.stderr:
            click.echo(l, err=True)
        sys.exit(1)

    if sleep:
        time.sleep(5)
        click.echo('Done')
    sys.exit(0)

@cli.command(name='stop')
@click.argument('nickname')
@click.option('--sleep', default=10)
def stop_command(nickname, sleep):
    if sleep > 0:
        msg = 'Server going down in {} seconds...'.format(sleep)
        click.echo(msg)
        say(nickname, msg)
        time.sleep(sleep)
    send(nickname, 'stop')

@cli.command(name='say')
@click.argument('nickname')
@click.argument('message')
def say_command(nickname, message):
    say(nickname, message)

@cli.command(name='backup')
@click.argument('nickname')
@click.argument('root', type=click.Path(exists=True))
@click.argument('backupdir', type=click.Path(exists=True))
def backup_command(nickname, root, backupdir):
    if not os.path.isfile(os.path.join(root, 'server.jar')):
        raise ValueError('Invalid root dir. Server file not found')
    fname = '{}-backup-{}.tar.7z'.format(nickname, time.strftime('%Y_%m_%d_%H%M%S', time.gmtime()))
    archive = os.path.join(backupdir, fname)
    click.echo('Starting backup of {}...'.format(nickname))
    say(nickname, 'Starting server backup.')
    send(nickname, 'save-off')
    time.sleep(1)
    send(nickname, 'save-all')
    time.sleep(5)
    result = create_backup(root, archive)
    send(nickname, 'save-on')
    time.sleep(1)
    say(nickname, 'Server backup complete')
    click.echo('Done')
    sys.exit(result)

def send(nickname, cmd):
    session = tmux.find_where({ 'session_name': nickname })
    session.cmd('send-keys', cmd)
    session.cmd('send-keys', 'Enter')

def say(nickname, msg):
    send(nickname, 'say {}.'.format(msg))

def create_backup(root, archive):
    try:
        click.echo('Backing up {} to {}'.format(root, archive))
        tar = subprocess.Popen(['tar', '-cf', '-', '-C', root, '.'], stdout=subprocess.PIPE)
        compress = subprocess.Popen(['7z', 'a', '-si', archive], stdin=tar.stdout, stdout=subprocess.PIPE)
        tar.stdout.close()
        output, error = compress.communicate()
        if compress.returncode is not 0:
            click.echo('Create archive failed:', err=True)
            click.echo(error, err=True)
        return compress.returncode
    except:
        click.echo('Create archive failed.', err=True)
        return 1

