# Google Cloud Platform (GCP) Setup Guide

To run this application, you need to set up a Google Cloud Project and enable the Drive and Sheets APIs.

## Steps

1.  **Create a Project**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project (e.g., "DOC-Extractor").

2.  **Enable APIs**:
    *   Go to **APIs & Services > Library**.
    *   Search for and enable **Google Drive API**.
    *   Search for and enable **Google Sheets API**.

3.  **Configure OAuth Consent Screen**:
    *   Go to **APIs & Services > OAuth consent screen**.
    *   Select **External** (or Internal if you have a Workspace organization) and click **Create**.
    *   Fill in the required fields (App name, User support email, Developer contact information).
    *   Click **Save and Continue**.
    *   **Scopes**: Add `.../auth/drive.readonly` and `.../auth/spreadsheets`.
    *   **Test Users**: Add your Google email address to the Test Users list.
    *   Save and Continue to Summary.

4.  **Create Credentials**:
    *   Go to **APIs & Services > Credentials**.
    *   Click **Create Credentials > OAuth client ID**.
    *   Application type: **Desktop app**.
    *   Name: "Desktop Client" (or any name).
    *   Click **Create**.

5.  **Download Credentials**:
    *   Download the JSON file.
    *   Rename it to `credentials.json`.
    *   Place it in the root directory of this project: `/Users/henryduong/antigrav/COCQ-Management/credentials.json`.

## Verification
After placing `credentials.json`, run `python src/auth.py`. A browser window will open asking you to login. Once authorized, a `token.json` file will be created.
