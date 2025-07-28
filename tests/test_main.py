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
    post = mocker.patch.object(main.client, 'chat_postMessage', return_value={'ts': '1'})
    data = {
        'event': {
            'type': 'app_mention',
            'client_msg_id': '123',
            'channel': 'C',
            'text': 'hello',
            'ts': '1.23',
            'user': 'U1'
        }
    }
    main.BOT_USER_ID = 'B'
    main.handle_event(data)
    post.assert_called_once()

