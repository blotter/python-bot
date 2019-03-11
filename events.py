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

def handle_delete_branch(irc, data):
    author = colorize(data['pusher']['name'], 'bold', 'irc')
    action = colorize('deleted', 'red', 'irc')

    branch = data['ref'].split('/')[-1]
    branch = colorize(branch, 'bold-blue', 'irc')

    irc.schedule_message("{} {} {} {}"
            .format(fmt_repo(data), author, action, branch))

def handle_push_event(irc, data):
    if data['forced']:
        handle_force_push(irc, data)
    elif data['deleted']:
        handle_delete_branch(irc, data)
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


def handle_issue(irc, data):
    repo = fmt_repo(data)
    user = colorize(data['sender']['login'], 'bold', 'irc')

    action = data['action']
    if not action in ['opened', 'closed']:
        return
    action_color = 'red' if action == 'opened' else 'green'
    action = colorize(action, action_color, 'irc')

    issue_num = colorize('#' + str(data['issue']['number']), 'bold-blue', 'irc')
    title = data['issue']['title']
    link = short_gh_link(data['issue']['html_url'])

    irc.schedule_message('{} {} {} issue {}: {} ({})'
            .format(repo, user, action, issue_num, title, link))

def handle_status_event(irc, data):
    if data['state'] == 'success':
        color = 'bold-green'
    elif data['state'] == 'error':
        color = 'red'
    elif data['state'] == 'failure':
        color = 'bold-red'
    elif data['state'] == 'pending':
        return
        color = 'bold-teal'
    else:
        print('Status: {}'.format(data['state']))
        color = 'black'

    repo = fmt_repo(data)
    repo_name = data['repository']['full_name']
    after_id = data['sha'][:12]
    befor_id = data['commit']['parents'][0]['sha'][:12]
    commit_id = colorize(after_id, 'bold', 'irc')
    desc = colorize(data['description'], color, 'irc')
    target_url = data['target_url'].split('?', 1)[0]
    change_url = 'https://github.com/{}/compare/{}...{}'.format(repo_name, befor_id, after_id)
    change = colorize('Change view:', 'teal', 'irc')
    build = colorize('Build details:', 'teal', 'irc')
    commit_msg = colorize(data['commit']['commit']['message'], 'green', 'irc')
    branch = colorize(data['branches'][0]['name'], 'bold-blue', 'irc')

    irc.schedule_message('{} {} on {}: {}'
            .format(repo, commit_id, branch, desc))
    irc.schedule_message('{} {} {}'
            .format(change, commit_msg, short_gh_link(change_url)))
    irc.schedule_message('{} {}'
            .format(build, target_url))

    print('Status event')

def handle_ping_event(irc, data):
    print("Ping event")

def handle_event(irc, event, data):
    if event == 'ping':
        handle_ping_event(irc, data)
    elif event == 'push':
        handle_push_event(irc, data)
    elif event == 'pull_request':
        handle_pull_request(irc, data)
    elif event == 'issues':
        handle_issue(irc, data)
    elif event == 'status':
        handle_status_event(irc, data)
    else:
        print("Unknown event type: " + event)
    print('handle_event: {}'.format(event))
