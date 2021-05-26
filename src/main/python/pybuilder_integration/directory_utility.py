import os
import shutil


def prepare_reports_directory(project):
    return prepare_directory("$dir_reports", project)


def prepare_logs_directory(project):
    return prepare_directory("$dir_logs", project)


def prepare_dist_directory(project):
    return prepare_directory("$dir_dist", project)


def prepare_directory(dir_variable, project):
    package__format = f"{dir_variable}/integration"
    reports_dir = project.expand_path(package__format)
    return _ensure_directory_exists(reports_dir)


def _ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def get_working_distribution_directory(project):
    dist_directory = prepare_dist_directory(project)
    return _ensure_directory_exists(f"{dist_directory}/working")


def get_latest_distribution_directory(project):
    dist_directory = prepare_dist_directory(project)
    return _ensure_directory_exists(f"{dist_directory}/LATEST")


def get_latest_zipped_distribution_directory(project):
    dist_directory = prepare_dist_directory(project)
    return _ensure_directory_exists(f"{dist_directory}/LATEST/zipped")


def package_artifacts(project, test_dir, tool):
    # Make a copy for easy access in environment validation
    working_dir = get_working_distribution_directory(project)
    shutil.copytree(test_dir, f"{working_dir}/{tool}",dirs_exist_ok=True)
    # package a copy for distribution
    # zip up the test and add them to the integration test dist directory
    dist_directory = prepare_dist_directory(project)
    shutil.make_archive(base_name=f"{dist_directory}/{tool}-{project.name}",
                        format="zip",
                        root_dir=test_dir)
