"""Explicit Maven dependency evidence; no resolution, download or build."""
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath


def declared_version(project, meta, group, artifact):
    cache=project.__dict__.setdefault('_declared_dependency_versions',{})
    key=(meta['file'],group,artifact)
    if key in cache:return cache[key]
    for parent in PurePosixPath(meta['file']).parents:
        name=(parent/'pom.xml').as_posix()
        source=project.dependency_sources.get(name)
        if source is None:continue
        try:root=ET.fromstring(source)
        except ET.ParseError:continue
        dependencies=root.find('{*}dependencies')
        versions=[dependency.findtext('{*}version') for dependency in dependencies or ()
            if dependency.findtext('{*}groupId')==group and dependency.findtext('{*}artifactId')==artifact]
        if versions:
            value=versions[0] if len(set(versions))==1 else None
            cache[key]=value;return value
    cache[key]=None
    return None
