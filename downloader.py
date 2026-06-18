import shutil
import tempfile
import zipfile
from pathlib import Path

from playwright.async_api import Download

from utils import get_logger, extrair_numero_nf

logger = get_logger(__name__)


async def processar_download(
    download: Download,
    destino: Path,
    max_retries: int = 3,
) -> str | None:
    """Faz o download do ZIP, extrai o XML e retorna o numero da NF.

    Args:
        download: Objeto Download do Playwright.
        destino: Diretorio onde o XML sera salvo.
        max_retries: Numero maximo de tentativas em caso de falha.

    Returns:
        Numero da NF extraida, ou None em caso de erro.
    """
    logger.info("Iniciando download: %s", download.suggested_filename)

    for tentativa in range(1, max_retries + 1):
        try:
            # Diretorio temporario para salvar o ZIP
            with tempfile.TemporaryDirectory() as tmp_dir:
                zip_path: Path = Path(tmp_dir) / download.suggested_filename

                # Salva o ZIP
                await download.save_as(str(zip_path))

                if not zip_path.exists() or zip_path.stat().st_size == 0:
                    raise RuntimeError("Arquivo ZIP vazio ou nao salvo")

                # Extrai o XML do ZIP
                numero_nf = await _extrair_xml_do_zip(zip_path, destino)

                logger.info("XML salvo: NF_%s.xml", numero_nf)
                return numero_nf

        except Exception as e:
            logger.warning(
                "Tentativa %d/%d falhou para %s: %s",
                tentativa,
                max_retries,
                download.suggested_filename,
                e,
            )
            if tentativa == max_retries:
                logger.error(
                    "Download falhou apos %d tentativas: %s",
                    max_retries,
                    download.suggested_filename,
                )
                return None

    return None


async def _extrair_xml_do_zip(zip_path: Path, destino: Path) -> str:
    """Extrai o XML de dentro do ZIP e salva no diretorio de destino.

    Args:
        zip_path: Caminho do arquivo ZIP.
        destino: Diretorio onde salvar o XML.

    Returns:
        Numero da NF extraida.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        # Lista os arquivos dentro do ZIP
        arquivos = zf.namelist()

        # Filtra apenas arquivos .xml
        xmls = [a for a in arquivos if a.lower().endswith(".xml")]

        if not xmls:
            raise RuntimeError(f"Nenhum arquivo XML encontrado dentro do ZIP: {zip_path.name}")

        # Usa o primeiro XML encontrado
        nome_xml = xmls[0]
        numero_nf = extrair_numero_nf(Path(nome_xml).stem)

        # Extrai o XML para o diretorio de destino
        with zf.open(nome_xml) as origem:
            with open(destino / f"NF_{numero_nf}.xml", "wb") as xml_destino:
                shutil.copyfileobj(origem, xml_destino)

    return numero_nf
