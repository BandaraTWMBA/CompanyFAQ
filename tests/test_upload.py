from pathlib import Path

from fastapi.testclient import TestClient

from api import app


client = TestClient(app)


from unittest.mock import patch

@patch("api.publish_task")
def test_upload_endpoint_saves_and_summarizes_file(mock_publish):
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    for path in upload_dir.glob("*"):
        if path.is_file():
            path.unlink()

    response = client.post(
        "/upload",
        files=[("files", ("sample.txt", b"Alpha beta gamma. Delta epsilon zeta.", "text/plain"))],
    )

    assert response.status_code == 200
    data_list = response.json()
    assert isinstance(data_list, list)
    assert len(data_list) == 1
    data = data_list[0]
    assert data["status"] == "processing"
    assert data["summary"] == "Summary is being generated in the background..."

    saved_path = Path(data["saved_to"])
    assert saved_path.exists()

    mock_publish.assert_called_once_with({
        "file_name": "sample.txt",
        "task": "process_file"
    })


def test_list_files_endpoint():
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    # Clean uploads directory helper files we might have created
    for name in ["doc_1.txt", "doc_2.pdf", "doc_2.content.txt", "doc_2.pdf.summary.txt"]:
        path = upload_dir / name
        if path.exists():
            path.unlink()

    # Create dummy files
    (upload_dir / "doc_1.txt").write_text("Hello", encoding="utf-8")
    (upload_dir / "doc_2.pdf").write_text("Hello PDF", encoding="utf-8")
    (upload_dir / "doc_2.content.txt").write_text("Extracted text", encoding="utf-8")
    (upload_dir / "doc_2.pdf.summary.txt").write_text("Summary text", encoding="utf-8")

    try:
        response = client.get("/files")
        assert response.status_code == 200
        files = response.json()
        assert "doc_1.txt" in files
        assert "doc_2.pdf" in files
        assert "doc_2.content.txt" not in files
        assert "doc_2.pdf.summary.txt" not in files
    finally:
        for name in ["doc_1.txt", "doc_2.pdf", "doc_2.content.txt", "doc_2.pdf.summary.txt"]:
            path = upload_dir / name
            if path.exists():
                path.unlink()


def test_get_file_summary_endpoint():
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)

    file_name = "test_summary_file.txt"
    file_path = upload_dir / file_name
    summary_path = file_path.with_suffix(file_path.suffix + ".summary.txt")

    file_path.write_text("Original document content.", encoding="utf-8")
    summary_path.write_text("Short summarized version.", encoding="utf-8")

    try:
        response = client.get(f"/files/{file_name}/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Short summarized version."

        # Test non-existent file
        response_non_existent = client.get("/files/non_existent.txt/summary")
        assert response_non_existent.status_code == 200
        data_non_existent = response_non_existent.json()
        assert "background" in data_non_existent["summary"]
    finally:
        if file_path.exists():
            file_path.unlink()
        if summary_path.exists():
            summary_path.unlink()
