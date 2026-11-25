"""Os testes usam um modelo falso: rodam sem rede, sem chave e sem custo."""

from datetime import datetime

import pytest

from agrupamento import Grupo, agrupar
from diagnostico import Diagnostico
from ia import EXEMPLOS, ClassificadorIA, configuracao_llm, montar_mensagens
from leitura import Evento

RESPOSTA = Diagnostico(
    gravidade="alta",
    categoria="bug",
    causa_provavel="Divisão por zero no cálculo de consumo.",
    acao_sugerida="Validar o divisor.",
)


class ModeloFalso:
    """Imita a interface usada do LangChain: with_structured_output e invoke."""

    def __init__(self, resposta):
        self.resposta = resposta
        self.formato_pedido = None
        self.opcoes_pedidas = None
        self.mensagens_recebidas = None

    def with_structured_output(self, formato, **opcoes):
        self.formato_pedido = formato
        self.opcoes_pedidas = opcoes
        return self

    def invoke(self, mensagens):
        self.mensagens_recebidas = mensagens
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


def criar_grupo(exemplos=None, trecho_traceback=None):
    return Grupo(
        assinatura="teste",
        nivel="ERROR",
        modulo="faturamento",
        quantidade=13,
        primeiro=datetime(2026, 11, 10, 7, 14),
        ultimo=datetime(2026, 11, 10, 11, 54),
        exemplos=exemplos or ["Erro ao calcular consumo médio"],
        trecho_traceback=trecho_traceback or ["ZeroDivisionError: division by zero"],
    )


def test_devolve_o_diagnostico_do_modelo():
    modelo = ModeloFalso(RESPOSTA)

    diagnostico = ClassificadorIA(llm=modelo).diagnosticar(criar_grupo())

    assert diagnostico == RESPOSTA
    assert modelo.formato_pedido is Diagnostico
    assert modelo.opcoes_pedidas == {"method": "json_schema"}


def test_prompt_tem_instrucoes_exemplos_e_o_grupo():
    mensagens = montar_mensagens(criar_grupo())

    papeis = [papel for papel, _ in mensagens]
    assert papeis[0] == "system"
    assert papeis.count("human") == len(EXEMPLOS) + 1
    assert papeis.count("ai") == len(EXEMPLOS)

    ultimo_papel, ultimo_texto = mensagens[-1]
    assert ultimo_papel == "human"
    assert "Ocorrências: 13 (de 07:14 a 11:54)" in ultimo_texto
    assert "ZeroDivisionError" in ultimo_texto


def test_so_dados_mascarados_chegam_ao_modelo():
    evento = Evento(
        momento=datetime(2026, 11, 10, 8, 0),
        nivel="ERROR",
        modulo="auth",
        mensagem="Falha para ana@email.com, CPF 030.564.139-53",
    )
    grupo = agrupar([evento])[0]
    modelo = ModeloFalso(RESPOSTA)

    ClassificadorIA(llm=modelo).diagnosticar(grupo)

    texto_enviado = "\n".join(texto for _, texto in modelo.mensagens_recebidas)
    assert "ana@email.com" not in texto_enviado
    assert "030.564.139-53" not in texto_enviado
    assert "<EMAIL>" in texto_enviado


def test_erro_do_modelo_nao_e_escondido():
    # O plano B é responsabilidade da cascata, não do classificador.
    modelo = ModeloFalso(TimeoutError("a API demorou demais"))

    with pytest.raises(TimeoutError):
        ClassificadorIA(llm=modelo).diagnosticar(criar_grupo())


def test_resposta_fora_do_formato_vira_erro():
    modelo = ModeloFalso(None)  # alguns provedores devolvem None quando falham

    with pytest.raises(ValueError):
        ClassificadorIA(llm=modelo).diagnosticar(criar_grupo())


def test_sem_modelo_configurado_da_erro_claro(monkeypatch):
    monkeypatch.delenv("LUPA_MODELO", raising=False)

    with pytest.raises(RuntimeError, match="LUPA_MODELO"):
        ClassificadorIA()


def test_configuracao_para_o_vllm(monkeypatch):
    monkeypatch.setenv("LUPA_MODELO", "openai:Qwen/Qwen2.5-7B-Instruct")
    monkeypatch.setenv("LUPA_BASE_URL", "http://workstation:8000/v1")
    monkeypatch.delenv("LUPA_API_KEY", raising=False)

    configuracao = configuracao_llm()

    assert configuracao["model"] == "openai:Qwen/Qwen2.5-7B-Instruct"
    assert configuracao["base_url"] == "http://workstation:8000/v1"
    assert configuracao["api_key"] == "EMPTY"
    assert configuracao["temperature"] == 0


def test_configuracao_sem_servidor_proprio(monkeypatch):
    monkeypatch.setenv("LUPA_MODELO", "openai:nome-do-modelo")
    monkeypatch.delenv("LUPA_BASE_URL", raising=False)

    configuracao = configuracao_llm()

    assert "base_url" not in configuracao
    assert "api_key" not in configuracao
