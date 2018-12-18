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
        tmux = None

@cli.command(name='start')
@click.argument('nickname')
@click.argument('root', type=click.Path(exists=True))
@click.option('--sleep/--no-sleep', default=True)
def start_command(nickname, root, sleep):
    if not os.path.isfile(os.path.join(root, 'server.jar')):
        raise ValueError('Invalid root dir. Server file not found')

    if sleep:
        click.echo('Starting server...')

    if not start_server(root, nickname):
        click.echo('Unable to start new session', err=True)
        sys.exit(1)

    if sleep:
        time.sleep(5)
        click.echo('Done')

    sys.exit(0)

@cli.command(name='stop')
@click.argument('nickname')
@click.option('--grace', default=10)
def stop_command(nickname, grace):
    if is_running(nickname):
        stop_server(nickname, grace)

@cli.command(name='restart')
@click.argument('nickname')
@click.argument('root', type=click.Path(exists=True))
@click.option('--grace', default=10)
@click.option('--backup/--no-backup', default=False)
@click.option('--backupdir', type=click.Path(exists=True))
def restart_command(nickname, root, grace, backup, backupdir):
    if not os.path.isfile(os.path.join(root, 'server.jar')):
        raise ValueError('Invalid root dir. Server file not found')

    if is_running(nickname):
        click.echo('Stopping {}...'.format(nickname))
        stop_server(nickname, grace)

    retries = 0
    max_retries = 10
    while is_running(nickname) and retries < max_retries:
        time.sleep(1)
        retries = retries + 1

    if retries >= max_retries:
        click.echo('Server not stopping. Unable to restart.', err=True)
        sys.exit(1)

    if backup:
        if os.path.isdir(backupdir):
            click.echo('Starting backup of {}...'.format(nickname))
            fname = '{}-backup-{}.tar.7z'.format(nickname, time.strftime('%Y_%m_%d_%H%M%S', time.gmtime()))
            archive = os.path.join(backupdir, fname)
            result = create_backup(root, archive)
            if result is not 0:
                click.echo('Unable to backup.', err=True)
                sys.exit(result)
        elif not backupdir:
            click.echo('Backup dir must be provided use "--backupdir".', err=True)
            sys.exit(1)
        else:
            click.echo('Unable to find backup dir "{}".'.format(backupdir), err=True)
            sys.exit(1)


    if not start_server(root, nickname):
        click.echo('Unable to start new session', err=True)
        sys.exit(1)

    time.sleep(5)
    click.echo('Done')
    sys.exit(0)


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

    if is_running(nickname):
        say(nickname, 'Starting server backup.')
        send(nickname, 'save-off')
        time.sleep(1)
        send(nickname, 'save-all')
        time.sleep(5)

    result = create_backup(root, archive)

    if is_running(nickname):
        send(nickname, 'save-on')
        time.sleep(1)
        say(nickname, 'Server backup complete')

    click.echo('Done')
    sys.exit(result)

# @cli.command(name='prune')
# @click.argument('nickname')
# @click.argument('backupdir', type=click.Path(exists=True))
# def prune_command(nickname, backupdir):
#     fname = '{}-backup-{}.tar.7z'.format(nickname, time.strftime('%Y_%m_%d_%H%M%S', time.gmtime()))
#     archive = os.path.join(backupdir, fname)
#     click.echo('Pruning backups of {}...'.format(nickname))
#
#     if is_running(nickname):
#         send(nickname, 'save-on')
#         time.sleep(1)
#         say(nickname, 'Server backup complete')
#
#     click.echo('Done')
#     sys.exit(result)

def start_server(root, nickname):
    server_cmd = 'cd {}; java -Xmx1024M -Xms1024M -d64 -jar server.jar nogui'.format(root)
    click.echo(server_cmd)

    res = tmux.cmd('new-session', '-d', '-s', nickname, server_cmd)
    if res.stderr:
        for l in res.stderr:
            click.echo(l, err=True)
        return False

    return True

def stop_server(nickname, grace_time = 0):
    if is_running(nickname):
        if grace_time > 0:
            msg = 'Server going down in {} seconds...'.format(grace_time)
            click.echo(msg)
            say(nickname, msg)
            time.sleep(grace_time)
        send(nickname, 'stop')
    else:
        click.echo('Server not running')


def is_running(nickname):
    if tmux is not None:
        try:
            session = tmux.find_where({ 'session_name': nickname })
            return session is not None
        except:
            return False
    else:
        return False

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

