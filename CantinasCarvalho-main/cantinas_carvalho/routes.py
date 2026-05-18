import os
import random
from flask_mail import Message
from functools import wraps

from flask import render_template, redirect, url_for, session, request, flash, jsonify
from flask_login import login_user, login_required, current_user
from werkzeug.utils import secure_filename

from cantinas_carvalho import app, bcrypt, db, mail
from cantinas_carvalho.forms import ComumRegisterForm, FuncionarioRegisterForm, LoginForm, ProdutoForm
from cantinas_carvalho.models import Usuario, UsuarioAluno, UsuarioFuncionario, ItemCardapio, Administrador, Categoria

from cantinas_carvalho.models import Categoria, ItemCardapio, Pedido, ItemVenda

carrinho = []

# Criação do @admin_required
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        admin = Administrador.query.filter_by(
            id_usuario=current_user.id_usuario
        ).first()

        if not admin:
            flash('Acesso permitido apenas para administradores.', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)

    return decorated_function


# =========================
# HOME
# =========================
@app.route("/")
def index():

    # Busca todos os produtos
    produtos = ItemCardapio.query.all()

    return render_template(
        "index.html",
        produtos=produtos
    )

# =========================
# CADASTRO ALUNO
# =========================
@app.route('/cadastarAlunos', methods=['GET', 'POST'])
def cadastrarAluno():
    register_form = ComumRegisterForm()

    if register_form.validate_on_submit():
        senha_hash = bcrypt.generate_password_hash(
            register_form.senha.data
        ).decode('utf-8')

        novo_usuario = Usuario(
            nome=register_form.nome.data,
            email=register_form.email.data,
            senha_hash=senha_hash,
            telefone=register_form.telefone.data,
            salt = os.urandom(16).hex()
        )

        db.session.add(novo_usuario)
        db.session.commit()

        aluno = UsuarioAluno(id_usuario=novo_usuario.id_usuario)
        db.session.add(aluno)
        db.session.commit()

        return redirect(url_for('listarCardapio'))

    return render_template('cadastroAlunos.html', form=register_form)


# =========================
# CADASTRO FUNCIONARIO
# =========================
@app.route('/cadastrarFuncionario', methods=['GET', 'POST'])
def cadastrarFuncionario():
    register_form = FuncionarioRegisterForm()

    if register_form.validate_on_submit():
        senha_hash = bcrypt.generate_password_hash(
            register_form.senha.data
        ).decode('utf-8')

        novo_usuario = Usuario(
            nome=register_form.nome.data,
            email=register_form.email.data,
            senha_hash=senha_hash,
            telefone=register_form.telefone.data,
            salt = os.urandom(16).hex()
        )

        db.session.add(novo_usuario)
        db.session.commit()

        funcionario = UsuarioFuncionario(
            id_usuario=novo_usuario.id_usuario,
            nif=register_form.nif.data
        )

        db.session.add(funcionario)
        db.session.commit()

        return redirect(url_for('listarCardapio'))

    return render_template('cadastroFuncionario.html', form=register_form)


# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=login_form.email.data).first()

        if usuario and bcrypt.check_password_hash(usuario.senha_hash, login_form.senha.data):

            admin = Administrador.query.filter_by(id_usuario=usuario.id_usuario).first()
            if admin:
                login_user(usuario)
                definir_perfil(usuario)
                return redirect(url_for('listarCardapio'))

            funcionario = UsuarioFuncionario.query.filter_by(id_usuario=usuario.id_usuario).first()
            if funcionario:
                login_user(usuario)
                definir_perfil(usuario)
                return redirect(url_for('listarcardapio'))

            aluno = UsuarioAluno.query.filter_by(id_usuario=usuario.id_usuario).first()
            if aluno:
                login_user(usuario)
                definir_perfil(usuario)
                return redirect(url_for('listarCardapio'))
        else:
            flash('Email ou senha inválidos')

    return render_template('login.html', form=login_form)

def definir_perfil(usuario):
    if Administrador.query.filter_by(id_usuario=usuario.id_usuario).first():
        session['perfil'] = 'admin'

    elif UsuarioFuncionario.query.filter_by(id_usuario=usuario.id_usuario).first():
        session['perfil'] = 'funcionario'

    elif UsuarioAluno.query.filter_by(id_usuario=usuario.id_usuario).first():
        session['perfil'] = 'aluno'

    else:
        session['perfil'] = 'desconhecido'

@app.route('/esqueceuSenha', methods=['GET', 'POST']) # Aceita GET para abrir a página
def esqueceuSenha(): # Mudei o nome da função para combinar com o seu url_for
    if request.method == 'POST':
        email_usuario = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email_usuario).first()

        if usuario:
            codigo = str(random.randint(1000, 9999))
            session['codigo'] = codigo
            session['email_usuario'] = usuario.id_usuario

            # Lógica de envio de e-mail (mantenha como estava)
            email_mensagem = Message(
                subject='Recuperação de Senha | Cantinas Carvalho',
                sender=app.config['MAIL_USERNAME'],
                recipients=[email_usuario]
            )
            email_mensagem.body = f"Olá, {usuario.nome}! Seu código de verificação é: {codigo}"
            mail.send(email_mensagem)

            return "E-mail enviado com sucesso!"
        else:
            return "Este e-mail não está cadastrado!", 404

    # Se o método for GET (clicou no link), ele apenas abre a página
    return render_template('RedefinirSenha.html')


# Rota de CARDÁPIO
@app.route("/categorias", methods=["GET"])
def listarCategorias():
    categorias_banco = Categoria.query.all()

    categorias = []

    for categoria in categorias_banco:
        categorias.append({
            "id": categoria.id_categoria,
            "nome": categoria.nome
        })

    return render_template('cardapio.html')

@app.route("/cardapio", methods=["GET"])
def listarCardapio():
    id_categoria = request.args.get('categoria')

    categorias = Categoria.query.all()

    if id_categoria:
        produtos = ItemCardapio.query.filter_by(id_categoria=id_categoria, disponivel=True).all()

    else:
        produtos = ItemCardapio.query.filter_by(disponivel=True).all()

    return render_template('cardapio.html', categorias=categorias, produtos=produtos)

# Rota de carrinho
@app.route("/carrinho", methods=["POST"])
def adicionarCarrinho():

    dados = request.get_json()

    id_produto = dados["produto_id"]
    quantidade = dados["quantidade"]

    produto = ItemCardapio.query.get(id_produto)

    if not produto:

        return jsonify({
            "mensagem": "produto não encontrado!",
        }), 404

    item = {
        "id": produto.id_item_cardapio,
        "nome": produto.nome,
        "preco": float(produto.preco),
        "imagem": produto.imagem,
        "quantidade": quantidade
    }

    carrinho.append(item)

    return jsonify({
        "status": "sucesso",
        "produto_nome": produto.nome
    })

@app.route("/carrinho", methods=["GET"])
def listarCarrinho():

    valor_total = 0

    for item in carrinho:
        subtotal = item["preco"] * item["quantidade"]
        valor_total += subtotal

    return render_template('carrinho.html', valor_total=valor_total)

@app.route("/carrinho/<int:id_produto>", methods=["DELETE"])
def removerCarrinho(id_produto):

    for item in carrinho:

        if item["id"] == id_produto:

            carrinho.remove(item)

            return jsonify({
                "mensagem": "item removido"
            })

    return jsonify({
        "erro": "item não encontrado"
    }), 404

# Rota de pedido
@app.route("/pedido", methods=["POST"])
def criarPedido():
    dados = request.get_json()

    id_usuario = dados["id_usuario"]

    valor_total = 0

    for item in carrinho:
        valor_total += (item["preco"] * item["quantidade"])

    pedido = Pedido(id_usuario = id_usuario, valor_pedido = valor_total, qr_code_retirada="qr_teste", codigo_unico = "codigo_teste")

    db.session.add(pedido)
    db.session.commit()

    for item in carrinho:
        item_venda = ItemVenda(id_pedido = pedido.id_pedido, id_item_cardapio = item["id"], quantidade = item["quantidade"], valor_unitario = item["preco"])

        db.session.add(item_venda)

    db.session.commit()

    carrinho.clear()

    return jsonify({
        "mensagem": "pedido criado com sucesso",
        "id_pedido": pedido.id_pedido
    })

@app.route("/perfil")
@login_required
def perfilFuncionario():

    funcionario = UsuarioFuncionario.query.filter_by(id_usuario=current_user.id_usuario).first()

    if not funcionario:
        return redirect(url_for("listarCardapio"))

    return render_template("conta.html")



# =========================
# TELA ADMIN
# =========================
# @app.route('/admin')
# @login_required
# @admin_required


#=========================
# CADASTRAR PRODUTO
# =========================
@app.route('/admin/cadastrarProduto', methods=['GET', 'POST'])
@login_required
@admin_required
def cadastrarProduto():

    # Pegando as categorias do banco e o formulario de produto
    produtoForm = ProdutoForm()
    categorias = Categoria.query.all()

    produtoForm.categoria.choices = [
        (categoria.id_categoria, categoria.nome)
        for categoria in categorias
    ]

    # Cadastro do produto
    if produtoForm.validate_on_submit():

        # Pegando e salvando imagem
        imagem = produtoForm.imagem.data
        nome_arquivo = secure_filename(imagem.filename)

        caminho_imagem = os.path.join(app.root_path, 'static/img', nome_arquivo)

        imagem.save(caminho_imagem)

        # Cadastrando novo produto
        novo_produto = ItemCardapio(
            nome=produtoForm.nome.data,
            descricao=produtoForm.descricao.data,
            preco=produtoForm.preco.data,
            quantidade_estoque=produtoForm.quantidade_estoque.data,
            id_categoria=produtoForm.categoria.data,
            imagem=nome_arquivo
        )

        db.session.add(novo_produto)
        db.session.commit()

        flash('Produto cadastrado com sucesso.', 'success')

        return redirect(url_for('telaAdmin'))

    return render_template('telaAdmin.html', form=produtoForm)

