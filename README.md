# cloud-deploy-action

GitHub action to authenticate and consume StackSpot Cloud API.

_**Note**: This action is supported on all runners operating systems (`ubuntu`, `macos`, `windows`)_

## 📚 Usage

### Requirements

To get the account keys (`CLIENT_ID`, `CLIENT_KEY` and `CLIENT_REALM`), please login using a **ADMIN** user on the [StackSpot Portal](https://stackspot.com), and generate new keys at [https://stackspot.com/en/settings/access-token](https://stackspot.com/en/settings/access-token). The credential needs the role `cloud_platform` enables to successfully consume the API.

_Note: You can generate an [`application.yaml` file](https://github.com/stack-spot/cloud-deploy-action/blob/main/stackspot/application-new.yaml), directly on the StackSpot Portal._

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
          PARAMETERS: |
            PLACEHOLDER_1 >> VALUE_1
            PLACEHOLDER_2 >> VALUE_2
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
**PARAMETERS** | NO | N/A | Placeholder values to replace in APPLICATION_FILE
**VERBOSE** | NO | `false` | Whether to show extra logs during execution. (e.g: `true`).

* * *

## License

[Apache License 2.0](https://github.com/stack-spot/cloud-deploy-action/blob/main/LICENSE)

* * *

## Development

To test this action on this repository during internal development, please use the setup below:

### DEV environment

```yaml
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4.2.1
      - name: Deploy repo application
        uses: stack-spot/cloud-deploy-action@main
        id: deploy
        with:
          CLIENT_REALM: stackspot-dev
          CLIENT_ID: ${{ secrets.CLIENT_ID_DEV }}
          CLIENT_KEY: ${{ secrets.CLIENT_KEY_DEV }}
          APPLICATION_FILE: ${{ github.workspace }}/stackspot/application-dev.yaml
          IMAGE_TAG: latest
          VERBOSE: true
```

### STG environment

```yaml
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4.2.1
      - name: Deploy repo application
        uses: stack-spot/cloud-deploy-action@main
        id: deploy
        with:
          CLIENT_REALM: stackspot-stg
          CLIENT_ID: ${{ secrets.CLIENT_ID_STG }}
          CLIENT_KEY: ${{ secrets.CLIENT_KEY_STG }}
          APPLICATION_FILE: ${{ github.workspace }}/stackspot/application-stg.yaml
          IMAGE_TAG: latest
          VERBOSE: true
```