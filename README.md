# Virtual Studio Guide
A collection of code samples to help setup a virtual studio that accompany the white paper: 
https://www.conductortech.com/thought-leadership

Most of the samples require changes to reflect your particular settings below is a summary of the
necessary changes in order to get the samples working.

## sgtk-config
The collector needs to be added to SgTk Config environment. See the white paper for details.

## Shotgun event daemon
The Dockerfile is expecting you to place config files for Conductor and the Shotgun event daemon:

* `shotgun_daemon/files/shotgunEventDaemon.conf`
* `shotgun_daemon/files/conductor_config.yaml`

In addition to you site-specific settings, `shotgunEventDaemon.conf` should have the following set 
to work with the EFS definition in the Terraform scripts:
* `eventIdFile: /mount/shotgun-daemon-efs/shotgunEventDaemon.id`
* `pidFile: /var/log/shotgunEventDaemon/shotgunEventDaemon.pid`
* `logPath: /mount/shotgun-daemon-efs/logs`
* `paths: /mount/shotgun-daemon-efs/plugins`

It also expects the following environment variables to be available at runtime:
* AWS_ACCOUNT_ID
* AWS_ACCESS_KEY_ID
* AWS_SECRET_ACCESS_KEY
* AWS_DEFAULT_REGION
* AWS_REGION
* AWS_PROJECT_BUCKET
* CONDUCTOR_API_KEY
* SHOTGUN_SERVER
* SHOTGUN_SCRIPT_NAME
* SHOTGUN_SCRIPT_KEY