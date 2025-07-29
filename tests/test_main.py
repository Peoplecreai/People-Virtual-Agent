import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('SLACK_BOT_TOKEN', 'test-token')
os.environ.setdefault('GEMINI_API_KEY', 'test-key')
import main


def test_helloworld(mocker):
    mocker.patch.object(main.genai_client.models, 'generate_content', return_value=mocker.Mock(text='hi'))
    client = main.app.test_client()
    resp = client.get('/gemini')
    assert resp.status_code == 200
    assert resp.data.decode() == 'hi'


def test_handle_event_app_mention(mocker):
    mocker.patch.object(main.genai_client.models, 'generate_content', return_value=mocker.Mock(text='reply'))
    post = mocker.patch.object(main.client, 'chat_postMessage', return_value={'ts': '2'})
    data = {
        'event': {
            'type': 'app_mention',
            'client_msg_id': '123',
            'channel': 'C',
            'text': 'hello',
            'ts': '2.34',
            'user': 'U1'
        }
    }
    main.BOT_USER_ID = 'B'
    main.handle_event(data)
    post.assert_called_once()


def test_dm_greets_with_slack_name(mocker):
    mocker.patch.object(main, 'get_preferred_name', return_value=None)
    mocker.patch.object(main.client, 'users_info', return_value={'user': {'profile': {'display_name': 'Alice'}}})
    post = mocker.patch.object(main.client, 'chat_postMessage', return_value={'ts': '3'})
    data = {
        'event': {
            'type': 'message',
            'channel': 'D1',
            'text': 'hello',
            'ts': '2.34',
            'user': 'U1'
        }
    }
    main.BOT_USER_ID = 'B'
    main.handle_event(data)
    post.assert_called_once_with(channel='D1', text='Hola Alice, ¿cómo te puedo ayudar hoy?', mrkdwn=True, thread_ts='2.34')


def test_normalize_slack_id():
    assert main.normalize_slack_id('<@U1>') == 'U1'
    assert main.normalize_slack_id('https://app.slack.com/team/U2') == 'U2'


def test_get_preferred_name_from_sheet(mocker):
    os.environ['MY_GOOGLE_CREDS'] = '{}'
    os.environ['SHEET_ID'] = '1'
    creds = mocker.patch.object(main.Credentials, 'from_service_account_info', return_value='c')
    gclient = mocker.Mock()
    sheet = mocker.Mock()
    gclient.open_by_key.return_value = sheet
    worksheet = mocker.Mock()
    sheet.sheet1 = worksheet
    worksheet.get_all_records.return_value = [{'Slack ID': '<@U3|bob>', 'Name (first)': 'Bob'}]
    mocker.patch.object(main.gspread, 'authorize', return_value=gclient)
    assert main.get_preferred_name('U3') == 'Bob'


def test_dm_greets_with_preferred_name(mocker):
    mocker.patch.object(main, 'get_preferred_name', return_value='Bob')
    post = mocker.patch.object(main.client, 'chat_postMessage', return_value={'ts': '3'})
    data = {
        'event': {
            'type': 'message',
            'channel': 'D1',
            'text': 'hello',
            'ts': '3.45',
            'user': 'U3'
        }
    }
    main.BOT_USER_ID = 'B'
    main.handle_event(data)
    post.assert_called_once_with(channel='D1', text='Hola Bob, ¿cómo te puedo ayudar hoy?', mrkdwn=True, thread_ts='3.45')

