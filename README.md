# CDO Microservice PyBuilder Plugin
This plugin provides support for common microservice build/deployment tasks for the PyBuilder library.  This is done by providing Docker image build/push support as well as the creation of deployments within a Kubernetes cluster.

## Quick Start
In order to utilize this plugin, add the following line to your build.py file:
``` python
use_plugin("pypi:pybuilder_cdo)
```

## Supplied Tasks
* twine_upload - Uploads the generated artifact to the specified repository
* docker_package - This task provides Docker image creation support within the build process.
* docker_publish - Executes a Docker push command with the image built by the docker_package task.
* kubernetes_deploy - Deploy the image from docker_publish into a Kubernetes cluster.

## Supported Parameters
* twine_repo_key - Repository key for artifacts to be uploaded to.  This must be a section within your ".pypirc" file.
* docker_version - Override the project version and use this instead when tagging Docker images.
* docker_tag_prefix - Specifies a prefix for the tag applied to the resulting Docker image.  The full name of the tag will be constructed as "<docker_tag_prefix>/<project_name>:<project_version>"
* kubernetes_deployment - Specifies the location of the yaml file to use when calling kubectl create.
* docker_context - Defines the location of the intermediary Docker context to use when building an image.  This defaults to "$dir_target/context" and should not be modified by users of this plugin.
* dir_source_main_docker - Specifies the location of Docker content within the project structure.  The default location for this is "src/main/docker".