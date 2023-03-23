from django.conf import settings
from django.shortcuts import redirect
from rest_framework.reverse import reverse
from pulp_ansible.app.models import AnsibleDistribution
from pulp_ansible.app.models import CollectionVersion
from pulpcore.plugin.models import ContentArtifact


# https://github.com/pulp/pulp_ansible/blob/main/pulp_ansible/app/galaxy/v3/serializers.py#L266
def get_download_url(obj) -> str:
    """
    Get artifact download URL.
    """
    content_artifact = ContentArtifact.objects.select_related("artifact").filter(content=obj)
    if content_artifact.get().artifact:
        # distro_base_path = self.context.get("path", self.context["distro_base_path"])
        distro_base_path = "published"
        filename_path = obj.relative_path.lstrip("/")

        # Note: We're using ANSIBLE_API_HOSTNAME here instead of calling reverse with request=
        # because using the request context to generate the full URL causes the download URL
        # to be inaccessible when pulp is running behind a reverse proxy.
        host = settings.ANSIBLE_API_HOSTNAME.strip("/")
        path = reverse(
            settings.ANSIBLE_URL_NAMESPACE + "collection-artifact-download",
            kwargs={"distro_base_path": distro_base_path, "filename": filename_path},
        ).strip("/")

        return f"{host}/{path}"


# https://github.com/pulp/pulp_ansible/blob/main/pulp_ansible/app/galaxy/v3/views.py#L670
def get_collection_artifact_download_url(filename):

    """Download collection."""
    distro_base_path = "published"
    distribution = AnsibleDistribution.objects.get(base_path=distro_base_path)

    url = "{host}/{prefix}/{distro_base_path}/{filename}".format(
        host=settings.CONTENT_ORIGIN.strip("/"),
        prefix=settings.CONTENT_PATH_PREFIX.strip("/"),
        distro_base_path=distro_base_path,
        filename=filename,
    )

    if (
        distribution.content_guard
        and distribution.content_guard.pulp_type == "core.content_redirect"
    ):
        guard = distribution.content_guard.cast()
        url = guard.preauthenticate_url(url)

    return redirect(url)


counter = 0
for cv in CollectionVersion.objects.all().order_by('pulp_created'):
    counter += 1

    # redirected url
    dl_url = get_download_url(cv)

    # actual artifact download url
    artifact_url = get_collection_artifact_download_url(os.path.basename(dl_url))

    print((
        f"{counter},{cv.content_ptr_id},{cv.pulp_created},{cv.namespace},{cv.name},{cv.version}"
        + f",{cv.license[0]},{dl_url},{artifact_url.url}"
    ))
