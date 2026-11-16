"""Lê um currículo local e devolve apenas sugestões revisáveis."""
import io
import json
import sys
from zipfile import ZipFile

from defusedxml.ElementTree import fromstring
from pypdf import PdfReader

from .vagas import contem, normalizar

HABILIDADES = ("Python", "Java", "JavaScript", "TypeScript", "Angular", "React", "SQL",
               "Spring Boot", "C#", "C++", ".NET", "AWS", "Azure", "Docker", "Kubernetes",
               "Power BI", "Excel", "Figma", "UX", "Scrum")


def sugerir(dados, tipo):
    if not 0 < len(dados) <= 1024 * 1024:
        raise ValueError("Tamanho inválido")
    with io.BytesIO(dados) as arquivo:
        if tipo == "pdf" and dados.startswith(b"%PDF-"):
            pdf = PdfReader(arquivo)
            if pdf.is_encrypted:
                raise ValueError("PDF protegido")
            texto = " ".join(p.extract_text()[:50000] for p in pdf.pages[:10])
        elif tipo == "docx":
            with ZipFile(arquivo) as zipado:
                info = zipado.getinfo("word/document.xml")
                if info.file_size > 2 * 1024 * 1024:
                    raise ValueError("Documento extenso")
                xml = fromstring(zipado.read(info), forbid_dtd=True)
                ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                if xml.tag != ns + "document":
                    raise ValueError("Formato inválido")
                texto = " ".join(no.text or "" for no in xml.iter(ns + "t"))
        else:
            raise ValueError("Formato inválido")
    texto = normalizar(texto)
    return {"habilidades": [s for s in HABILIDADES if contem(texto, s)]}


if __name__ == "__main__":
    try:
        print(json.dumps(sugerir(sys.stdin.buffer.read(1024 * 1024 + 1), sys.argv[1])))
    except Exception:
        sys.exit(2)
