from tkinter import *
from tkinter import messagebox
from datetime import date
import sqlite3
import os
import re
from decimal import Decimal
from xml.sax.saxutils import escape


def valor_em_centavos(texto):
    """Aceita 150, 150,50, 1.234,50 ou 1234.50, sem arredondar a entrada."""
    texto = str(texto).strip()
    if texto.startswith('R$'):
        texto = texto[2:].strip()
    if not texto or len(texto) > 20:
        raise ValueError('Informe um valor, por exemplo: 150,00.')
    if ',' in texto:
        if not re.fullmatch(r'(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+),[0-9]{1,2}', texto):
            raise ValueError('Valor inválido. Use, por exemplo, 150,00 ou 1.234,50.')
        texto = texto.replace('.', '').replace(',', '.')
    elif re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{3})+', texto):
        texto = texto.replace('.', '')
    elif not re.fullmatch(r'[0-9]+(?:\.[0-9]{1,2})?', texto):
        raise ValueError('Informe um valor positivo com até duas casas decimais.')
    valor = Decimal(texto)
    if valor > Decimal('999999999.99'):
        raise ValueError('O valor máximo por item é R$ 999.999.999,99.')
    return int(valor * 100)


def formatar_reais(centavos):
    """Calcula e apresenta dinheiro com centavos inteiros, sem erro de float."""
    inteiro, fracao = divmod(centavos, 100)
    return f'R$ {inteiro:,}'.replace(',', '.') + f',{fracao:02d}'


def gerar_pdf_orcamento(caminho, cliente, placa, itens, observacoes='', responsavel=''):
    """Gera a tabela do orçamento, com cabeçalho repetido e total calculado."""
    # Importação sob demanda: o restante do programa abre sem ReportLab instalado.
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
    )
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Fontes incluídas no próprio ReportLab: o PDF tem a mesma aparência
    # no Windows e em outros sistemas, sem depender das fontes do computador.
    fontes = os.path.join(os.path.dirname(reportlab.__file__), 'fonts')
    for nome, arquivo in (('OficinaPDF', 'Vera.ttf'), ('OficinaPDF-Bold', 'VeraBd.ttf')):
        if nome not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nome, os.path.join(fontes, arquivo)))

    if not cliente.strip() or not itens:
        raise ValueError('Informe o cliente e adicione pelo menos um item.')
    for item in itens:
        if not item['descricao'].strip() or len(item['descricao']) > 300:
            raise ValueError('Cada descrição deve ter de 1 a 300 caracteres.')
        if type(item['centavos']) is not int or item['centavos'] < 0:
            raise ValueError('Valor de item inválido.')

    verde = colors.HexColor('#354F43')
    cinza = colors.HexColor('#5C6561')
    estilos = getSampleStyleSheet()
    corpo = ParagraphStyle('OrcCorpo', parent=estilos['Normal'], fontName='OficinaPDF',
                           fontSize=10, leading=15, textColor=colors.HexColor('#252D29'))
    pequeno = ParagraphStyle('OrcPequeno', parent=corpo, fontSize=9, leading=13,
                             textColor=cinza)
    titulo = ParagraphStyle('OrcTitulo', parent=corpo, fontName='OficinaPDF-Bold',
                            fontSize=25, leading=30, textColor=verde)
    subtitulo = ParagraphStyle('OrcSecao', parent=corpo, fontName='OficinaPDF-Bold',
                               fontSize=12, leading=18, textColor=verde)
    cabecalho = ParagraphStyle('OrcCabecalho', parent=corpo, fontName='OficinaPDF-Bold',
                               fontSize=9, textColor=colors.white)
    direita = ParagraphStyle('OrcDireita', parent=corpo, alignment=TA_RIGHT)
    cabecalho_direita = ParagraphStyle('OrcCabDireita', parent=cabecalho, alignment=TA_RIGHT)

    def par(texto, estilo=corpo):
        # Escape impede que '<', '&' e outras entradas sejam interpretadas como marcação.
        return Paragraph(escape(str(texto)).replace('\n', '<br/>'), estilo)

    documento = SimpleDocTemplate(
        str(caminho), pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
        topMargin=19*mm, bottomMargin=21*mm, title='Orçamento de serviços',
        author=responsavel or 'Gestão de Oficina',
    )
    largura = A4[0] - 40*mm
    hoje = date.today().strftime('%d/%m/%Y')
    conteudo = [par('MECÂNICA AUTOMOTIVA', pequeno), Spacer(1, 4*mm),
                par('Orçamento', titulo), Spacer(1, 3*mm),
                par(f'Emitido em {hoje}', pequeno), Spacer(1, 9*mm)]
    dados = Table([
        [par('CLIENTE', pequeno), par('PLACA DO VEÍCULO', pequeno)],
        [par(cliente.strip()), par(placa.strip().upper() or 'Não informada')],
    ], colWidths=[largura*0.68, largura*0.32])
    dados.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F1F4F2')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 12),
    ]))
    conteudo.extend([dados, Spacer(1, 9*mm), par('Serviços e peças', subtitulo),
                     Spacer(1, 3*mm)])
    linhas = [[par('ITEM', cabecalho), par('DESCRIÇÃO', cabecalho),
               par('VALOR (R$)', cabecalho_direita)]]
    for numero, item in enumerate(itens, 1):
        linhas.append([par(numero, pequeno), par(item['descricao']),
                       par(formatar_reais(item['centavos']), direita)])
    tabela = Table(linhas, colWidths=[18*mm, largura-63*mm, 45*mm], repeatRows=1,
                   hAlign='LEFT')
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), verde),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7F8F7')]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, verde),
        ('LINEBELOW', (0, 1), (-1, -1), 0.4, colors.HexColor('#DEE4DF')),
    ]))
    conteudo.append(tabela)
    total = sum(item['centavos'] for item in itens)
    total_estilo = ParagraphStyle('OrcTotal', parent=direita, fontName='OficinaPDF-Bold',
                                  fontSize=15, leading=20, textColor=verde)
    resumo = Table([[par('TOTAL DO ORÇAMENTO', subtitulo),
                     par(formatar_reais(total), total_estilo)]],
                   colWidths=[largura*0.55, largura*0.45])
    resumo.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8EFEA')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 13),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 13),
    ]))
    conteudo.append(KeepTogether([Spacer(1, 4*mm), resumo]))
    if observacoes.strip():
        conteudo.extend([Spacer(1, 8*mm), par('Observações', subtitulo),
                         Spacer(1, 2*mm), par(observacoes.strip())])
    if responsavel.strip():
        conteudo.extend([Spacer(1, 6*mm), par(f'Responsável: {responsavel.strip()}', pequeno)])

    def rodape(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#DEE4DF'))
        canvas.line(20*mm, 16*mm, A4[0]-20*mm, 16*mm)
        canvas.setFont('OficinaPDF', 8)
        canvas.setFillColor(cinza)
        canvas.drawString(20*mm, 11*mm, 'Orçamento de serviços e peças')
        canvas.drawRightString(A4[0]-20*mm, 11*mm, f'Página {doc.page}')
        canvas.restoreState()

    documento.build(conteudo, onFirstPage=rodape, onLaterPages=rodape)

class Funcoes():

    def limpar_tela(self):
        self.entry_id_cliente.delete(0, END)
        self.entry_nome.delete(0, END)
        self.entry_cpf.delete(0, END)
        self.entry_telefone.delete(0, END)
        self.entry_endereco.delete(0, END)
        for campo in (self.entry_placa, self.entry_marca, self.entry_modelo, self.entry_ano):
            campo.delete(0, END)
        self.id_veiculo = None

    def connect_bd(self):
        self.cnt = sqlite3.connect('bd_oficina')
        self.cnt.execute('PRAGMA foreign_keys = ON') # Ativa a verificação das relações entre as tabelas nesta conexão.
        self.cursor = self.cnt.cursor() # O cursor executa comandos SQL e recupera seus resultados.

    def disconnect_bd(self):
        self.cnt.close()

    def criar_bd(self):
        self.connect_bd()
        print('Conectando banco de dados')
        self.cursor.execute('''
CREATE TABLE IF NOT EXISTS clientes (
id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
nome TEXT NOT NULL,
cpf TEXT NOT NULL UNIQUE,
telefone TEXT NOT NULL,
endereco TEXT NOT NULL
)
''')
        self.cursor.execute('''
CREATE TABLE IF NOT EXISTS veiculos (
id_veiculo INTEGER PRIMARY KEY AUTOINCREMENT,
id_cliente INTEGER NOT NULL,
placa TEXT NOT NULL UNIQUE,
marca TEXT NOT NULL,
modelo TEXT NOT NULL,
ano INTEGER,

FOREIGN KEY (id_cliente) REFERENCES clientes (id_cliente)
)
''')
        self.cursor.execute('''
CREATE TABLE IF NOT EXISTS ordens_servico (
id_ordem INTEGER PRIMARY KEY AUTOINCREMENT,
id_veiculo INTEGER NOT NULL,
data_abertura TEXT,
descricao TEXT NOT NULL,
status TEXT DEFAULT 'Aberto',
valor REAL DEFAULT 0,

FOREIGN KEY (id_veiculo) REFERENCES veiculos(id_veiculo)
)        
''')
        self.cnt.commit()
        print('Banco de dados criado...')
        self.disconnect_bd()
        print('Desconectando banco de dados...')

    def obter_dados_clientes(self):
        self.id_cliente = self.entry_id_cliente.get()
        self.nome = self.entry_nome.get()
        self.cpf = self.entry_cpf.get()
        self.telefone = self.entry_telefone.get()
        self.endereco = self.entry_endereco.get()

    def cadastrar_cliente(self):
        self.obter_dados_clientes() # strip() retira espaços nas extremidades. # upper() padroniza a placa em letras maiúsculas.
        self.placa = self.entry_placa.get().strip().upper()
        self.marca = self.entry_marca.get().strip()
        self.modelo = self.entry_modelo.get().strip()
        self.ano = self.entry_ano.get().strip()
        if not all((self.nome, self.cpf, self.telefone, self.endereco,  # all() verifica se todos os campos listados têm conteúdo.
                    self.placa, self.marca, self.modelo)):
            messagebox.showwarning('Cadastro', 'Preencha os dados do cliente e do veículo.') # Caso não tenha conteúdo em algum dos campos ele exibe essa mensagem box.
            return
        if self.ano and not self.ano.isdigit(): # Se um ano foi digitado, ele precisa conter somente dígitos.
            messagebox.showwarning('Cadastro', 'O ano deve ser numérico.')
            return
        self.connect_bd()
        try: # Os dois INSERTs ficam na mesma transação. # Se ocorrer um erro, o cliente não fica salvo sem o veículo.
            with self.cnt:
                self.cursor.execute('''
INSERT INTO clientes (
nome,
cpf,
telefone,
endereco)

VALUES (?, ?, ?, ?)

''', (self.nome, self.cpf, self.telefone, self.endereco))
                self.cursor.execute('''INSERT INTO veiculos
                    (id_cliente, placa, marca, modelo, ano) VALUES (?, ?, ?, ?, ?)''',
                    (self.cursor.lastrowid, self.placa, self.marca, self.modelo, # lastrowid recupera o ID criado no INSERT do cliente. # Esse ID será usado para vincular o veículo ao cliente.
                     int(self.ano) if self.ano else None)) # Se não houver ano, salva NULL no banco.
        except sqlite3.IntegrityError as erro: # Trata erros como CPF ou placa já cadastrados. # as erro guarda o erro para que possamos mostrar seu detalhe.
            messagebox.showerror('Cadastro', f'CPF ou placa duplicado, ou dados inválidos: {erro}')
            return
        finally: # finally é executado tanto em caso de sucesso quanto de erro.
            self.disconnect_bd()
        self.limpar_tela()
        self.exibir_clientes()

    def obter_dados_veiculos(self):
        self.id_veiculo = getattr(self, 'id_veiculo', None) # Leia assim: “Pegue o valor de id_veiculo deste objeto. Se ele ainda não existir, use None.”
        self.id_cliente = self.entry_id_cliente.get()
        self.placa = self.entry_placa.get()
        self.marca = self.entry_marca.get()
        self.modelo = self.entry_modelo.get()
        self.ano = self.entry_ano.get()

    def cadastrar_veiculo(self):  # Cadastra outro veículo para um cliente já existente.
        self.obter_dados_veiculos()
        self.connect_bd()
        self.cursor.execute('''
INSERT INTO veiculos (
id_cliente,
placa,
marca,
modelo,
ano)

VALUES (?, ?, ?, ?, ?)
''', (self.id_cliente, self.placa, self.marca, self.modelo, self.ano))

        self.cnt.commit()
        print('Veiculo cadastrado com sucesso')
        self.disconnect_bd()

    def obter_dados_ordem(self):
        self.placa_os = self.entry_os_placa.get().strip().upper()
        self.descricao = self.entry_descricao.get('1.0', END).strip() # '1.0' representa o início: linha 1, posição 0. # lê o conteúdo desde a linha 1, posição 0 até o fim. Essa forma de indicar posições é usada no widget Text do Tkinter.
        valor = self.entry_valor.get().strip() # Inicialmente o valor digitado é uma string.

        # Converte o formato brasileiro para o formato aceito por float().
        # Exemplo: "1.234,50" se transforma em "1234.50".
        if ',' in valor:
            valor = valor.replace('.', '').replace(',', '.') 
        self.valor = float(valor) if valor else 0.0 # Se o campo estiver vazio, usa zero.

    def cadastrar_ordem(self): # Cadastra uma ordem de serviço para um veículo existente.
        try:
            self.obter_dados_ordem()
        except ValueError:
            messagebox.showwarning('O.S.', 'Informe um valor numérico.') # Box para mensagem caso não seja obtido nenhum valor para OS
            return
        if not self.placa_os or not self.descricao: # A ordem precisa de uma placa e de uma descrição.
            messagebox.showwarning('O.S.', 'Informe a placa e a descrição.') 
            return

        # Procura o ID do veículo correspondente à placa.
        # fetchone() devolve uma linha ou None, caso não encontre nada.
        self.connect_bd()
        veiculo = self.cursor.execute('SELECT id_veiculo FROM veiculos WHERE placa=?',
                                      (self.placa_os,)).fetchone()
        if not veiculo:
            self.disconnect_bd()
            messagebox.showwarning('O.S.', 'Placa não cadastrada.')
            return

        # veiculo[0] contém o ID encontrado.
        # date.today().isoformat() produz uma data como "2026-09-25".
        # Como status não é informado, o banco usa o padrão "Aberto".
        self.cursor.execute('''
INSERT INTO ordens_servico (
id_veiculo,
data_abertura,
descricao,
valor)

VALUES (?, ?, ?, ?)
''', (veiculo[0], date.today().isoformat(), self.descricao, self.valor))

        self.cnt.commit()
        print('Ordem de serviço cadastrada com sucesso')
        self.disconnect_bd()
        self.limpar_os()
        self.exibir_clientes()

    def limpar_os(self): # Limpa os campos de pesquisa e edição da ordem de serviço.
        self.entry_num_os.delete(0, END)
        self.entry_os_placa.delete(0, END)
        self.entry_descricao.delete('1.0', END) # Em um widget Text, o início é indicado por '1.0'.
        self.entry_valor.delete(0, END)

    def exibir_clientes(self): # Consulta o banco e reconstrói as linhas da tabela na tela.

        # get_children() fornece as linhas atuais da Treeview.
        # O * passa cada linha como um argumento para delete().
        self.tv.delete(*self.tv.get_children())
        self.connect_bd()

        self.cursor.execute('''
SELECT c.id_cliente, c.nome, c.telefone, v.marca || ' ' || v.modelo,
       v.placa, o.id_ordem, o.valor, v.id_veiculo
FROM clientes c
LEFT JOIN veiculos v ON v.id_cliente = c.id_cliente
LEFT JOIN ordens_servico o ON o.id_ordem = (
  SELECT MAX(id_ordem) FROM ordens_servico WHERE id_veiculo = v.id_veiculo)
ORDER BY c.nome, v.placa
''')
        clientes = self.cursor.fetchall()

        #-- c, v e o são apelidos para as tabelas.
        #-- || junta marca, um espaço e modelo em uma única coluna.
        #-- LEFT JOIN mantém o cliente no resultado mesmo que ele não tenha veículo.
        #-- A subconsulta procura o maior ID de ordem daquele veículo.
        #-- Assim, a lista mostra a ordem mais recente em termos de ID.

        self.veiculos_linhas = {} # Relaciona cada linha visual ao ID do veículo correspondente.
        for i in clientes:
            item = self.tv.insert('', END, values=(i[0], i[1], i[2], i[3] or '',
                i[4] or '', i[5] or '', f'{i[6]:.2f}' if i[6] is not None else ''))
            self.veiculos_linhas[item] = i[7] # i[7] é o ID do veículo, guardado para uso no duplo clique.

            # i[0] a i[6] são as sete colunas visíveis na Treeview.
            # Campos sem valor aparecem como texto vazio.
            # O valor monetário aparece com duas casas decimais.

        self.disconnect_bd()

    def editar_cliente(self): # Atualiza o cliente e o veículo selecionados no formulário.
        self.obter_dados_clientes()
        self.obter_dados_veiculos()
        if not self.id_cliente or not self.id_veiculo: # É necessário os IDs para ele saber qual veículo editar
            messagebox.showwarning('Edição', 'Dê dois cliques no registro antes de editar.')
            return

        self.connect_bd()
        try:
            with self.cnt:
                self.cursor.execute('''
UPDATE clientes
SET nome = ?, cpf = ?, telefone = ?, endereco = ?
WHERE id_cliente = ?
''', (self.nome, self.cpf, self.telefone, self.endereco, self.id_cliente))
                self.cursor.execute('''UPDATE veiculos SET placa=?, marca=?, modelo=?, ano=?
                    WHERE id_veiculo=? AND id_cliente=?''',
                    (self.placa.upper(), self.marca, self.modelo,
                     int(self.ano) if self.ano else None, self.id_veiculo, self.id_cliente))
        except (sqlite3.IntegrityError, ValueError) as erro: # Trata, por exemplo, uma placa duplicada ou um ano inválido.
            messagebox.showerror('Edição', str(erro))
            return
        finally:
            self.disconnect_bd()

        self.limpar_tela()
        self.exibir_clientes()

        print('Cliente alterado com sucesso!')

    def excluir_cliente(self):
        self.obter_dados_clientes()
        if not self.id_cliente:
            messagebox.showwarning('Exclusão', 'Dê dois cliques no cliente antes de excluir.')
            return
        if not messagebox.askyesno('Excluir', 'Excluir cliente, veículos e todas as suas O.S.?'):  # askyesno() devolve True se a pessoa confirmar a exclusão.
            return

        self.connect_bd()
        # Apaga na ordem: ordens, veículos e, por último, cliente.
        # Essa ordem respeita as relações entre as tabelas.
        with self.cnt: # Como a tabela cliente é a que possui a informação do veiculo e a veiculo possui informação da ordem, devemos excluir primeiro os dados da ordem, depois veiculo e depois cliente
            self.cursor.execute('''DELETE FROM ordens_servico WHERE id_veiculo IN
                (SELECT id_veiculo FROM veiculos WHERE id_cliente=?)''', (self.id_cliente,))
            self.cursor.execute('DELETE FROM veiculos WHERE id_cliente=?', (self.id_cliente,))
            self.cursor.execute('''
DELETE FROM clientes
WHERE id_cliente = ?
''', (self.id_cliente,))
        self.disconnect_bd()

        self.limpar_tela()
        self.exibir_clientes()

        print('Cliente excluído com sucesso!')

    def duplo_click_cliente(self, event):
        selecionado = self.tv.selection()

        if selecionado: # Trabalha com a primeira linha selecionada.
            item = selecionado[0]
            id_cliente = self.tv.item(item, 'values')[0] # O ID do cliente está na primeira coluna da linha.
            id_veiculo = self.veiculos_linhas.get(item) # Descobre o ID do veículo associado àquela linha.
            self.connect_bd()
            cliente = self.cursor.execute('SELECT nome,cpf,telefone,endereco FROM clientes WHERE id_cliente=?', # Busca informações do cliente que não estão todas visíveis na lista.
                                          (id_cliente,)).fetchone()
            veiculo = self.cursor.execute('SELECT placa,marca,modelo,ano FROM veiculos WHERE id_veiculo=?', # Só faz a consulta de veículo se a linha tiver um veículo.
                                          (id_veiculo,)).fetchone() if id_veiculo else None
            self.disconnect_bd()
            self.limpar_tela()
            self.id_veiculo = id_veiculo

            # zip() combina cada campo com o valor que deve receber.
            # *cliente expande nome, CPF, telefone e endereço.
            for campo, valor in zip((self.entry_id_cliente, self.entry_nome, self.entry_cpf,
                                      self.entry_telefone, self.entry_endereco), (id_cliente, *cliente)):
                campo.insert(0, str(valor))
            if veiculo:
                for campo, valor in zip((self.entry_placa, self.entry_marca,
                                          self.entry_modelo, self.entry_ano), veiculo):
                    campo.insert(0, '' if valor is None else str(valor))
                self.entry_os_placa.delete(0, END) # Também coloca a placa na área de ordens de serviço.
                self.entry_os_placa.insert(0, veiculo[0])

    def pesquisar_os(self):
        numero = self.entry_num_os.get().strip() # Se número e placa estiverem preenchidos, o número tem prioridade.
        placa = self.entry_os_placa.get().strip().upper()
        if not numero and not placa:
            messagebox.showwarning('Pesquisa', 'Informe número da O.S. ou placa.')
            return
        self.connect_bd()
        if numero:
            dados = self.cursor.execute('''SELECT o.id_ordem,v.placa,o.descricao,o.valor
                FROM ordens_servico o JOIN veiculos v ON v.id_veiculo=o.id_veiculo
                WHERE o.id_ordem=?''', (numero,)).fetchone()
        else: # Pela placa, procura a O.S. com o maior ID.
            dados = self.cursor.execute('''SELECT o.id_ordem,v.placa,o.descricao,o.valor
                FROM ordens_servico o JOIN veiculos v ON v.id_veiculo=o.id_veiculo
                WHERE v.placa=? ORDER BY o.id_ordem DESC LIMIT 1''', (placa,)).fetchone()
        self.disconnect_bd()

        # fetchone() devolve None se não encontrar uma ordem.
        if not dados:
            messagebox.showinfo('Pesquisa', 'O.S. não encontrada.')
            return
        self.limpar_os()
        self.entry_num_os.insert(0, str(dados[0]))
        self.entry_os_placa.insert(0, dados[1])
        self.entry_descricao.insert('1.0', dados[2])
        self.entry_valor.insert(0, f'{dados[3]:.2f}')

    def editar_ordem(self): # Altera placa vinculada, descrição e valor de uma O.S
        numero = self.entry_num_os.get().strip()
        if not numero:
            messagebox.showwarning('O.S.', 'Pesquise a O.S. antes de editar.')
            return
        try:
            self.obter_dados_ordem()
        except ValueError:
            messagebox.showwarning('O.S.', 'Valor inválido.')
            return
        self.connect_bd()
        veiculo = self.cursor.execute('SELECT id_veiculo FROM veiculos WHERE placa=?', # Verifica se a placa informada pertence a um veículo cadastrado.
                                      (self.placa_os,)).fetchone()
        if not veiculo or not self.descricao:
            self.disconnect_bd()
            messagebox.showwarning('O.S.', 'Informe placa cadastrada e descrição.')
            return
        with self.cnt: # O UPDATE não altera data_abertura nem status.
            self.cursor.execute('''UPDATE ordens_servico SET id_veiculo=?, descricao=?, valor=?
                WHERE id_ordem=?''', (veiculo[0], self.descricao, self.valor, numero))
            alterados = self.cursor.rowcount # rowcount informa quantas linhas foram atingidas pelo UPDATE.
        self.disconnect_bd()
        if not alterados:
            messagebox.showwarning('O.S.', 'O.S. não encontrada.')
            return
        self.limpar_os()
        self.exibir_clientes()

    def excluir_ordem(self):
        numero = self.entry_num_os.get().strip()
        if not numero:
            messagebox.showwarning('O.S.', 'Pesquise a O.S. antes de excluir.')
            return
        if not messagebox.askyesno('Excluir', f'Excluir O.S. nº {numero}?'):
            return
        self.connect_bd()
        with self.cnt:
            self.cursor.execute('DELETE FROM ordens_servico WHERE id_ordem=?', (numero,))
            excluidos = self.cursor.rowcount
        self.disconnect_bd()
        if not excluidos:
            messagebox.showwarning('O.S.', 'O.S. não encontrada.')
            return
        self.limpar_os()
        self.exibir_clientes()
