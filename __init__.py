from pybuilder.core import init
from git import Repo
from git.exc import InvalidGitRepositoryError

from .tasks import *


@init()
def initialize(project):
    try:
        repo = Repo()
        active_branch = repo.active_branch
        git_hash = active_branch.commit.hexsha
        f = filter(lambda t: t.commit.hexsha == git_hash, repo.tags)
        tags = list(map(lambda t: t.name, f))

        project.set_property("git_active_tags", tags)
        project.set_property("git_active_branch", active_branch.name)
        project.set_property("git_active_hash", git_hash)
        project.set_property("git_active_short_hash", git_hash[:7])
    except Exception:
        pass

    project.set_property("docker_context", "$dir_target/context")
    project.set_property("dir_source_main_docker", "src/main/docker")
