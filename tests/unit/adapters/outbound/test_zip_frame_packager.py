"""Tests for the ZipFramePackager class"""

import zipfile

import pytest
from pytest_mock import MockerFixture

from video_processor.adapters.outbound import ZIPFramePackager
from video_processor.domain.exceptions import FramePackagingError
from video_processor.domain.value_objects import FileContent, RawFrame, TempFile


def test_should_package_frames_into_zip(mocker: MockerFixture):
    """Given a list of RawFrame objects
    When packaging the frames using ZIPFramePackager
    Then it should return a FileContent object with the path and content of the ZIP file
    """

    # Given
    temp_file_manager = mocker.Mock()
    temp_file = TempFile(path="temp.zip", content=b"")
    temp_file_manager.create.return_value = temp_file
    packager = ZIPFramePackager(temp_file_manager)
    frames = [
        RawFrame(index=0, filename="frame1.txt", content=b"frame1_content"),
        RawFrame(index=1, filename="frame2.txt", content=b"frame2_content"),
    ]

    zip_magic = mocker.MagicMock()
    zip_magic.__enter__.return_value = zip_magic
    mock_zipfile = mocker.patch(
        "video_processor.adapters.outbound.zip_frame_packager.zipfile.ZipFile",
        return_value=zip_magic,
    )

    mocked_open = mocker.mock_open(read_data=b"fake-zip-content")
    mocker.patch("builtins.open", mocked_open)

    # When
    result = packager.package(frames)

    # Then
    assert isinstance(result, FileContent)
    assert result.path == "temp.zip"
    assert result.content == b"fake-zip-content"
    mock_zipfile.assert_called_once_with("temp.zip", mode="w")
    zip_magic.writestr.assert_any_call("frame1.txt", b"frame1_content")
    zip_magic.writestr.assert_any_call("frame2.txt", b"frame2_content")
    temp_file_manager.create.assert_called_once_with(b"", suffix=".zip")
    temp_file_manager.delete.assert_called_once_with(temp_file)


def test_should_raise_error_on_packaging_failure(mocker: MockerFixture):
    """Given a list of RawFrame objects
    When an error occurs during packaging using ZIPFramePackager
    Then it should raise a FramePackagingError with an appropriate message
    """

    # Given
    temp_file_manager = mocker.Mock()
    temp_file = TempFile(path="temp.zip", content=b"")
    temp_file_manager.create.return_value = temp_file
    packager = ZIPFramePackager(temp_file_manager)
    frames = [
        RawFrame(index=0, filename="frame1.txt", content=b"frame1_content"),
        RawFrame(index=1, filename="frame2.txt", content=b"frame2_content"),
    ]

    mock_zipfile = mocker.patch(
        "video_processor.adapters.outbound.zip_frame_packager.zipfile.ZipFile",
        side_effect=zipfile.BadZipFile("Bad ZIP file"),
    )

    # When / Then
    with pytest.raises(FramePackagingError) as exc_info:
        packager.package(frames)

    assert str(exc_info.value) == (
        "An error occurred during frame packaging: Bad ZIP file"
    )
    temp_file_manager.create.assert_called_once_with(b"", suffix=".zip")
    temp_file_manager.delete.assert_called_once_with(temp_file)
    mock_zipfile.writestr.assert_not_called()
