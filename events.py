from colors import colorize
import subprocess
import requests

def fmt_repo(data):
    repo = '[' + data['repository']['full_name'] + ']'
    return colorize(repo, 'royal', 'irc')

# Use git.io to get a shortened link for commit names, etc. which are too long
def short_gh_link(link):
    conn = requests.post('https://git.io', data={'url':link})
    return conn.headers['Location']

MAX_COMMIT_LOG_LEN = 5
MAX_COMMIT_LEN = 70

def fmt_commit(cmt):
    hsh = colorize(cmt['id'][:10], 'teal', 'irc')
    author = colorize(cmt['author']['name'], 'bold-green', 'irc')
    message = cmt['message']
    message = message[:MAX_COMMIT_LEN] \
            + ('..' if len(message) > MAX_COMMIT_LEN else '')

    return '{} {}: {}'.format(hsh, author, message)

def fmt_last_commits(data):
    commits = list(map(fmt_commit, data['commits']))

    # make sure the commit list isn't too long
    if len(commits) <= MAX_COMMIT_LOG_LEN:
        return commits
    else:
        ellipsized_num = len(commits) - MAX_COMMIT_LOG_LEN + 1
        ellipsized = str(ellipsized_num) + ' more'
        last_shown = MAX_COMMIT_LOG_LEN - 1

        last_line = '... and {} commit' \
            .format(colorize(ellipsized, 'royal', 'irc'))
        if ellipsized_num > 1: # add s to commitS
            last_line += 's'

        return commits[slice(0, last_shown)] + [last_line]

def handle_force_push(irc, data):
    author = colorize(data['pusher']['name'], 'bold', 'irc')

    before = colorize(data['before'][:10], 'bold-red', 'irc')
    after = colorize(data['after'][:10], 'bold-red', 'irc')

    branch = data['ref'].split('/')[-1]
    branch = colorize(branch, 'bold-blue', 'irc')

    irc.schedule_message("{} {} force-pushed {} from {} to {} ({}):"
            .format(fmt_repo(data), author, branch, before, after, short_gh_link(data['compare'])))

    commits = fmt_last_commits(data)
    for commit in commits:
        irc.schedule_message(commit)

    print("Force push event")

def handle_forward_push(irc, data):
    author = colorize(data['pusher']['name'], 'bold', 'irc')

    num_commits = len(data['commits'])
    num_commits = str(num_commits) + " commit" + ('s' if num_commits > 1 else '')

    num_commits = colorize(num_commits, 'bold-teal', 'irc')

    branch = data['ref'].split('/')[-1]
    branch = colorize(branch, 'bold-blue', 'irc')

    irc.schedule_message("{} {} pushed {} to {} ({}):"
            .format(fmt_repo(data), author, num_commits, branch, short_gh_link(data['compare'])))

    commits = fmt_last_commits(data)
    for commit in commits:
        irc.schedule_message(commit)

    print("Push event")

def handle_push_event(irc, data):
    if data['forced']:
        handle_force_push(irc, data)
    else:
        handle_forward_push(irc, data)

def fmt_pr_action(action, merged):
    if action == 'opened' or action == 'reopened':
        action = colorize(action, 'green', 'irc')
    elif action == 'closed':
        if merged:
            action = colorize('merged', 'purple', 'irc')
        else:
            action = colorize(action, 'red', 'irc')
    else:
        action = colorize(action, 'brown', 'irc')

    return action

def handle_pull_request(irc, data):
    repo = fmt_repo(data)
    author = colorize(data['sender']['login'], 'bold', 'irc')
    action = fmt_pr_action(data['action'], data['pull_request']['merged'])
    pr_num = colorize('#' + str(data['number']), 'bold-blue', 'irc')
    title = data['pull_request']['title']
    link = short_gh_link(data['pull_request']['html_url'])

    irc.schedule_message('{} {} {} pull request {}: {} ({})'
            .format(repo, author, action, pr_num, title, link))

def handle_ping_event(irc, data):
    print("Ping event")

def handle_event(irc, event, data):
    if event == 'ping':
        handle_ping_event(irc, data)
    elif event == 'push':
        handle_push_event(irc, data)
    elif event == 'pull_request':
        handle_pull_request(irc, data)
    else:
        print("Unknown event type: " + event)
