import io
import uuid
import warnings
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError


def pasta_fotos(veiculo_id):
    return Path(current_app.config.get('VEICULO_UPLOAD_ROOT') or
                Path(current_app.static_folder) / 'uploads' / 'veiculos') / str(veiculo_id)


def preparar_foto(arquivo):
    bruto = arquivo.stream.read(10 * 1024 * 1024 + 1)
    if not bruto or len(bruto) > 10 * 1024 * 1024:
        raise ValueError('Cada foto deve ter até 10 MB.')
    if arquivo.mimetype not in ('image/jpeg', 'image/png', 'image/heic', 'image/heif'):
        raise ValueError('Use fotos JPG, PNG ou HEIC.')
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(bruto)) as imagem:
                permitidos = {'image/jpeg': ('JPEG',), 'image/png': ('PNG',),
                              'image/heic': ('HEIF',), 'image/heif': ('HEIF',)}
                if imagem.format not in permitidos[arquivo.mimetype] or imagem.width * imagem.height > 24_000_000:
                    raise ValueError('Foto inválida ou com dimensões excessivas.')
                imagem = ImageOps.exif_transpose(imagem).convert('RGB')
                imagem.thumbnail((1920, 1920))
                original = io.BytesIO()
                imagem.save(original, 'JPEG', quality=85)
                thumb = ImageOps.fit(imagem, (400, 300))
                pequeno = io.BytesIO()
                thumb.save(pequeno, 'JPEG', quality=80)
                return original.getvalue(), pequeno.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValueError('Não foi possível ler esta foto.') from None


def salvar_foto(veiculo_id, preparada):
    pasta = pasta_fotos(veiculo_id)
    pasta.mkdir(parents=True, exist_ok=True)
    filename = uuid.uuid4().hex + '.jpg'
    try:
        (pasta / filename).write_bytes(preparada[0])
        (pasta / (filename[:-4] + '_thumb.jpg')).write_bytes(preparada[1])
    except OSError:
        remover_foto(veiculo_id, filename)
        raise
    return filename


def remover_foto(veiculo_id, filename):
    pasta = pasta_fotos(veiculo_id)
    for nome in (filename, filename[:-4] + '_thumb.jpg'):
        (pasta / nome).unlink(missing_ok=True)
