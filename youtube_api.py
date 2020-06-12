from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

flow = InstalledAppFlow.from_client_secrets_file(
    'client_secret.json',
    scopes=['profile', 'email'])

flow.run_local_server()
credentials = flow.credentials

youtube = build('youtube', 'v3', credentials=credentials)
request = youtube.channels().list(part='statistics', forUsername='sentdex')
response = request.execute()
print(response)
