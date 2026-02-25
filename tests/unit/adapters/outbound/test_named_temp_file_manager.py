"""Tests for the NamedTempFileManager class"""

import os

import pytest

from video_processor.adapters.outbound import NamedTempFileManager
from video_processor.domain.exceptions import TempFileManagerError
from video_processor.domain.value_objects import TempFile


def test_should_create_temp_file():
    """Given content and a suffix
    When creating a temporary file using the NamedTempFileManager
    Then it should return a TempFile with a valid path and the file should exist
    """

    # Given
    manager = NamedTempFileManager()

    content = b"Test content"
    suffix = ".txt"

    # When
    temp_file = manager.create(content, suffix)

    # Then
    assert isinstance(temp_file, TempFile)
    assert temp_file.path.endswith(suffix)
    assert os.path.exists(temp_file.path)

    # Cleanup
    manager.delete(temp_file)


def test_should_raise_error_on_create_failure(mocker):
    """Given a failure when creating a temporary file
    When creating a temporary file using the NamedTempFileManager
    Then it should raise a TempFileManagerError
    """

    # Given
    manager = NamedTempFileManager()
    mocker.patch("tempfile.NamedTemporaryFile", side_effect=IOError("Mocked error"))

    content = b"Test content"
    suffix = ".txt"

    # When / Then
    with pytest.raises(TempFileManagerError) as exc_info:
        manager.create(content, suffix)

    assert "Failed to create temporary file" in str(exc_info.value)


def test_should_delete_temp_file():
    """Given a TempFile that exists
    When deleting the TempFile using the NamedTempFileManager
    Then the file should be deleted and no longer exist
    """

    # Given
    manager = NamedTempFileManager()
    temp_file = manager.create(b"Test content", ".txt")

    # When
    manager.delete(temp_file)

    # Then
    assert not os.path.exists(temp_file.path)


def test_should_raise_error_on_delete_failure(mocker):
    """Given a failure when deleting a temporary file
    When deleting a TempFile using the NamedTempFileManager
    Then it should raise a TempFileManagerError
    """

    # Given
    manager = NamedTempFileManager()
    temp_file = manager.create(b"Test content", ".txt")
    mocker.patch("os.remove", side_effect=IOError("Mocked error"))

    # When / Then
    with pytest.raises(TempFileManagerError) as exc_info:
        manager.delete(temp_file)

    assert "Failed to delete temporary file" in str(exc_info.value)

    # Cleanup
    os.unlink(temp_file.path)


def test_should_get_size_of_temp_file():
    """Given a TempFile that exists
    When getting the size of the TempFile using the NamedTempFileManager
    Then it should return the correct size in bytes
    """

    # Given
    manager = NamedTempFileManager()
    content = b"Test content"
    temp_file = manager.create(content, ".txt")

    # When
    size = manager.get_size(temp_file)

    # Then
    assert size == len(content)

    # Cleanup
    manager.delete(temp_file)


def test_should_raise_error_on_get_size_failure(mocker):
    """Given a failure when getting the size of a temporary file
    When getting the size of a TempFile using the NamedTempFileManager
    Then it should raise a TempFileManagerError
    """

    # Given
    manager = NamedTempFileManager()
    temp_file = manager.create(b"Test content", ".txt")
    mocker.patch("os.path.getsize", side_effect=IOError("Mocked error"))

    # When / Then
    with pytest.raises(TempFileManagerError) as exc_info:
        manager.get_size(temp_file)

    assert "Failed to get file size" in str(exc_info.value)

    # Cleanup
    manager.delete(temp_file)
