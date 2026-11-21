"""Fronteira de escrita SQLite: dados pessoais não são gravados nem em respostas recusadas.

O Agno persiste antes de devolver o RunOutput à aplicação, inclusive no caminho de erro.
Sanitizamos cópias nas APIs de escrita, preservando a resposta original para a barreira
recusar o conteúdo indevido. Não há limpeza retroativa de bancos existentes.
"""

from agno.db.sqlite import SqliteDb

from seguranca.filtro_pii import mascarar_estrutura


class SqliteDbProtegido(SqliteDb):
    """SqliteDb do Agno 3.0.9 com sanitização de sessões, execuções e memórias."""

    def upsert_run(self, run, session_id, user_id=None, run_index=None):
        dados = mascarar_estrutura(run if isinstance(run, dict) else run.to_dict())
        seguro = dados if isinstance(run, dict) else type(run).from_dict(dados)
        return super().upsert_run(seguro, session_id=session_id, user_id=user_id, run_index=run_index)

    @staticmethod
    def _sessao_segura(session):
        # O Agno 3 grava execuções via upsert_run, mas também as devolve ao chamador
        # no objeto da sessão. Preservamos esse contrato com cópias sanitizadas.
        return type(session).from_dict(mascarar_estrutura(session.to_dict()))

    def upsert_session(self, session, deserialize=True):
        return super().upsert_session(self._sessao_segura(session), deserialize=deserialize)

    def upsert_sessions(self, sessions, deserialize=True, preserve_updated_at=False):
        return super().upsert_sessions(
            [self._sessao_segura(s) for s in sessions], deserialize=deserialize,
            preserve_updated_at=preserve_updated_at)

    @staticmethod
    def _memoria_segura(memory):
        return type(memory).from_dict(mascarar_estrutura(memory.to_dict()))

    def upsert_user_memory(self, memory, deserialize=True):
        return super().upsert_user_memory(self._memoria_segura(memory), deserialize=deserialize)

    def upsert_memories(self, memories, deserialize=True, preserve_updated_at=False):
        return super().upsert_memories(
            [self._memoria_segura(m) for m in memories], deserialize=deserialize,
            preserve_updated_at=preserve_updated_at)

    def upsert_tool_result(self, row):
        return super().upsert_tool_result(mascarar_estrutura(row))
