from __future__ import annotations

from neural_link.runtime import service


def test_unit_file_tem_as_seccoes_esperadas():
    conteudo = service.unit_file_content(
        python_executable="/usr/bin/python3",
        working_directory="/opt/neural-link",
    )
    assert "[Unit]" in conteudo
    assert "[Service]" in conteudo
    assert "[Install]" in conteudo
    assert "Restart=always" in conteudo
    assert "ExecStart=/usr/bin/python3 -m neural_link.runtime.main" in conteudo
    assert "WorkingDirectory=/opt/neural-link" in conteudo


def test_install_escreve_num_diretorio_temporario_sem_tocar_no_systemd(tmp_path):
    destino = service.install(
        python_executable="/usr/bin/python3",
        working_directory="/opt/neural-link",
        systemd_dir=tmp_path,
        enable=True,  # mesmo pedindo, só chama systemctl se for o caminho REAL
    )
    assert destino == tmp_path / service.NOME_SERVICO
    assert destino.is_file()
    assert "[Unit]" in destino.read_text()


def test_uninstall_remove_o_ficheiro(tmp_path):
    service.install(python_executable="/usr/bin/python3",
                     working_directory="/opt/neural-link", systemd_dir=tmp_path)
    service.uninstall(systemd_dir=tmp_path)
    assert not (tmp_path / service.NOME_SERVICO).exists()


def test_uninstall_sem_ficheiro_nao_rebenta(tmp_path):
    service.uninstall(systemd_dir=tmp_path)
