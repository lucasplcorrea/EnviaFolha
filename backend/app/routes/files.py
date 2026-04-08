"""HTTP route handlers for generic file uploads used by frontend flows."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from app.routes.base import BaseRouter


class FilesRouter(BaseRouter):
    """Router para upload genérico de arquivos (PDF/imagens)."""

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

    def handle_post(self, path: str):
        if path == '/api/v1/files/upload' or path == '/api/v1/uploads/csv':
            self.handle_upload_file()
            return

        self.send_error('Endpoint não encontrado', 404)

    def _parse_boundary(self, content_type: str) -> str | None:
        for part in (content_type or '').split(';'):
            if 'boundary=' in part:
                return part.split('boundary=')[1].strip()
        return None

    def _uploads_dir(self) -> Path:
        backend_root = Path(__file__).resolve().parents[2]
        uploads = backend_root / 'uploads'
        uploads.mkdir(parents=True, exist_ok=True)
        return uploads

    def handle_upload_file(self):
        try:
            content_type = self.handler.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json_response({'error': 'Content-Type deve ser multipart/form-data'}, 400)
                return

            boundary = self._parse_boundary(content_type)
            if not boundary:
                self.send_json_response({'error': 'Boundary não encontrado'}, 400)
                return

            content_length = int(self.handler.headers.get('Content-Length', 0))
            if content_length <= 0:
                self.send_json_response({'error': 'Corpo da requisição vazio'}, 400)
                return

            if content_length > self.MAX_FILE_SIZE_BYTES + 1024 * 1024:
                self.send_json_response({'error': 'Arquivo excede o limite permitido'}, 413)
                return

            body = self.handler.rfile.read(content_length)
            boundary_bytes = f'--{boundary}'.encode()
            parts = body.split(boundary_bytes)

            file_data = None
            original_filename = None

            for part in parts:
                if not part or part in (b'--\r\n', b'--'):
                    continue

                if b'Content-Disposition' not in part or b'name="file"' not in part:
                    continue

                header_blob = part.split(b'\r\n\r\n', 1)[0].decode('utf-8', errors='ignore')
                filename_match = re.search(r'filename="([^"]+)"', header_blob)
                if filename_match:
                    original_filename = filename_match.group(1)

                split_point = part.find(b'\r\n\r\n')
                if split_point != -1:
                    file_data = part[split_point + 4:].rstrip(b'\r\n')
                break

            if not file_data or not original_filename:
                self.send_json_response({'error': 'Arquivo não enviado'}, 400)
                return

            file_size = len(file_data)
            if file_size > self.MAX_FILE_SIZE_BYTES:
                self.send_json_response({'error': 'Arquivo excede 25MB'}, 413)
                return

            _, ext = os.path.splitext(original_filename)
            ext = ext.lower()
            if not ext:
                ext = '.bin'

            safe_stem = re.sub(r'[^a-zA-Z0-9_-]+', '_', os.path.splitext(original_filename)[0]).strip('_')
            if not safe_stem:
                safe_stem = 'arquivo'

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            saved_filename = f'{safe_stem}_{timestamp}{ext}'
            saved_path = self._uploads_dir() / saved_filename

            with saved_path.open('wb') as output_file:
                output_file.write(file_data)

            self.send_json_response(
                {
                    'success': True,
                    'filename': saved_filename,
                    'original_name': original_filename,
                    'size': file_size,
                    'file_path': str(saved_path),
                    'uploaded_at': datetime.now().isoformat(),
                },
                200,
            )
        except Exception as ex:
            self.send_json_response({'error': f'Erro ao fazer upload: {str(ex)}'}, 500)
