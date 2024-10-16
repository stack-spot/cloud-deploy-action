# cloud-deploy-action

GitHub action to authenticate and consume StackSpot Cloud API.

_**Note**: This action is supported on all runners operating systems (`ubuntu`, `macos`, `windows`)_

## 📚 Usage

### Requirements

To get the account keys (`CLIENT_ID`, `CLIENT_KEY` and `CLIENT_REALM`), please login using a **ADMIN** user on the [StackSpot Portal](https://stackspot.com), and generate new keys at [https://stackspot.com/en/settings/access-token](https://stackspot.com/en/settings/access-token).

### Use Case

```yaml
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4.2.1
      - name: Deploy repo application
        uses: stack-spot/cloud-deploy-action@main
        id: deploy
        with:
          CLIENT_REALM: ${{ secrets.CLIENT_REALM }}
          CLIENT_ID: ${{ secrets.CLIENT_ID }}
          CLIENT_KEY: ${{ secrets.CLIENT_KEY }}
          APPLICATION_FILE: ${{ github.workspace }}/stackspot/application.yaml
          IMAGE_TAG: latest
          VERBOSE: true
```

* * *

## ▶️ Action Inputs

Field | Mandatory | Default Value | Observation
------------ | ------------  | ------------- | -------------
**CLIENT_ID** | YES | N/A | [StackSpot](https://stackspot.com/en/settings/access-token) Client ID.
**CLIENT_KEY** | YES | N/A |[StackSpot](https://stackspot.com/en/settings/access-token) Client KEY.
**CLIENT_REALM** | YES | N/A |[StackSpot](https://stackspot.com/en/settings/access-token) Client Realm.
**APPLICATION_FILE** | YES | N/A | StackSpot application config file (generally in `stackspot` folder)
**IMAGE_TAG** | YES | N/A | Image tag to use for deploy
**VERBOSE** | NO | `false` | Whether to show extra logs during execution. (e.g: `true`).

* * *

## License

[Apache License 2.0](https://github.com/stack-spot/cloud-deploy-action/blob/main/LICENSE)
