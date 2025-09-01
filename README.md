# 🎨 MyDraws - Coloring Book Creator

MyDraws é uma aplicação web Django que transforma suas imagens em desenhos para colorir usando processamento de imagem com OpenCV e inteligência artificial. A plataforma oferece conversão local e aprimoramento por IA, com sistema de créditos e autenticação de usuários.

## ✨ Funcionalidades

- 🖼️ **Conversão de Imagens**: Transforme fotos em desenhos para colorir usando OpenCV
- 🤖 **Aprimoramento por IA**: Melhore os desenhos usando Google Generative AI e OpenAI
- 📚 **Organização em Livros**: Organize suas criações em livros personalizados
- 💳 **Sistema de Créditos**: Sistema de pagamento integrado com Stripe e MercadoPago
- 👤 **Autenticação Social**: Login com Google via Django Allauth
- 🌐 **Internacionalização**: Suporte a múltiplos idiomas (PT-BR, EN)
- 📱 **Design Responsivo**: Interface moderna com Tailwind CSS
- ⚡ **Processamento Assíncrono**: Tasks em background com Celery e Redis

## 🛠️ Tecnologias

- **Backend**: Django 5.2.4, Python 3.13
- **Banco de Dados**: PostgreSQL, SQLite (desenvolvimento)
- **Processamento de Imagem**: OpenCV, Pillow
- **IA**: Google Generative AI, OpenAI
- **Frontend**: Tailwind CSS, JavaScript
- **Pagamentos**: Stripe, MercadoPago
- **Autenticação**: Django Allauth
- **Tasks Assíncronas**: Celery, Redis
- **Containerização**: Docker, Docker Compose

## 🚀 Instalação e Configuração

### Pré-requisitos

- Python 3.10+
- PostgreSQL (produção)
- Redis (para Celery)
- Docker e Docker Compose (opcional)

### 1. Clone o repositório

```bash
git clone https://github.com/PedroHenriqueDevBR/MyDraws.git
cd MyDraws
```

### 2. Configuração com Docker (Recomendado)

```bash
# Copie e configure as variáveis de ambiente
cp .env.example .env

# Inicie os serviços
docker-compose up -d

# Execute as migrações
docker-compose exec web python manage.py migrate

# Crie um superusuário
docker-compose exec web python manage.py createsuperuser
```

### 3. Configuração Manual

```bash
# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# Execute as migrações
python manage.py migrate

# Crie um superusuário
python manage.py createsuperuser

# Inicie o Redis (necessário para Celery)
redis-server

# Em outro terminal, inicie o Celery
celery -A bobbies_creator worker --loglevel=info

# Inicie o servidor de desenvolvimento
python manage.py runserver
```

## ⚙️ Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# Django
SECRET_KEY=sua-chave-secreta-super-segura
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# Banco de Dados
DATABASE_URL=postgresql://user:password@localhost:5432/mydraws

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Pagamentos
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Google AI
GENAI_API_KEY=your_api_key_here

# OpenAI
OPENAI_API_KEY=your_api_key_here
OPENAI_ORG_ID=your_org_id_here

# Autenticação Social
GOOGLE_OAUTH2_CLIENT_ID=seu-client-id
GOOGLE_OAUTH2_CLIENT_SECRET=seu-client-secret
```

## 📱 Como Usar

1. **Acesse a aplicação**: http://localhost:8000
2. **Cadastre-se ou faça login** usando email ou Google
3. **Faça upload de uma imagem** na página principal
4. **Escolha o tipo de conversão**:
   - Conversão local (OpenCV)
   - Aprimoramento por IA (requer créditos)
5. **Organize suas criações** em livros personalizados
6. **Compre créditos** para usar recursos premium

## 🏗️ Arquitetura do Projeto

### Estrutura de Diretórios

```
bobbies_creator/
├── bobbies_creator/          # Configurações principais do Django
│   ├── settings.py          # Configurações da aplicação
│   ├── urls.py              # URLs principais
│   ├── celery.py            # Configuração do Celery
│   └── wsgi.py              # WSGI para produção
├── core/                    # App principal
│   ├── models.py            # Modelos do banco de dados
│   ├── views.py             # Views e lógica de negócio
│   ├── forms.py             # Formulários Django
│   ├── tasks.py             # Tasks do Celery
│   ├── services/            # Serviços externos
│   │   ├── local_converter.py     # Conversão OpenCV
│   │   ├── design_by_ai.py        # IA Google
│   │   ├── design_by_openai.py    # IA OpenAI
│   │   └── mercado_pago.py        # Integração MercadoPago
│   ├── templates/           # Templates HTML
│   └── static/              # Arquivos estáticos
├── media/                   # Uploads de usuário
├── staticfiles/             # Arquivos estáticos coletados
├── locale/                  # Arquivos de tradução
├── dockerfiles/             # Dockerfiles customizados
└── docker-compose.yml       # Configuração Docker
```

### Modelos Principais

- **Profile**: Usuário customizado com sistema de créditos
- **Book**: Livros para organizar imagens
- **UploadedImage**: Imagens carregadas pelos usuários
- **CreditTransaction**: Histórico de transações de créditos

### Fluxo de Processamento de Imagem

1. **Upload**: Usuário faz upload da imagem
2. **Conversão Local**: OpenCV processa a imagem (gratuito)
3. **IA Opcional**: Aprimoramento usando IA (pago)
4. **Armazenamento**: Salva original e versões processadas
5. **Organização**: Adiciona ao livro do usuário

## 🎨 Algoritmo de Conversão

O processamento de imagem utiliza OpenCV com os seguintes passos:

```python
# 1. Conversão para escala de cinza
gray_image = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

# 2. Inversão de cores
inverted_image = 255 - gray_image

# 3. Aplicação de blur gaussiano (detail_level deve ser ímpar)
blurred_image = cv2.GaussianBlur(inverted_image, (detail_level, detail_level), 0)

# 4. Criação do sketch através de divisão
sketch = cv2.divide(gray_image, 255 - blurred_image, scale=256)
```

## 💳 Sistema de Créditos

### Pacotes Disponíveis

- **30 Créditos**: R$ 9,99
- **60 Créditos**: R$ 14,99 (15 créditos grátis)
- **100 Créditos**: R$ 24,99 (25 créditos grátis)

### Uso de Créditos

- Conversão local (OpenCV): **1 crédito por imagem**
- Aprimoramento por IA: **3 créditos por imagem**

## 🌐 Internacionalização (i18n)

O projeto suporta múltiplos idiomas usando o framework de internacionalização do Django. O idioma padrão é inglês, e português brasileiro também é suportado.

### Gerenciando Traduções

#### 1. Extrair Mensagens para Tradução

```bash
python manage.py makemessages -l pt_BR
```

#### 2. Editar Arquivos de Tradução

Edite os arquivos `.po` em `locale/pt_BR/LC_MESSAGES/django.po`:

```po
#: templates/base.html:13
msgid "Coloring Book"
msgstr "Livro de Colorir"

#: templates/base_site.html:15
msgid "You don't have enough credits"
msgstr "Você não possui créditos suficientes"
```

#### 3. Compilar Mensagens

```bash
python manage.py compilemessages
```

#### 4. Adicionar Novos Idiomas

1. Adicione o idioma em `settings.py`:
   ```python
   LANGUAGES = [
       ("en", "English"),
       ("pt-br", "Português (Brasil)"),
       ("es", "Español"),
   ]
   ```

2. Crie arquivos de mensagem para o novo idioma:
   ```bash
   python manage.py makemessages -l es
   ```

## 🚀 Deploy

### Produção com Docker

```bash
# Usando docker-compose.prod.yml
docker-compose -f docker-compose.prod.yml up -d

# Configurar Nginx como proxy reverso
# Arquivo de configuração em default.conf
```

### Variáveis de Ambiente para Produção

```env
DEBUG=False
ALLOWED_HOSTS=seudominio.com,www.seudominio.com
DATABASE_URL=postgresql://user:password@db:5432/mydraws_prod
CELERY_BROKER_URL=redis://redis:6379/0
```

### Checklist de Deploy

- [ ] Configurar variáveis de ambiente
- [ ] Configurar banco de dados PostgreSQL
- [ ] Configurar Redis para Celery
- [ ] Configurar servidor web (Nginx)
- [ ] Configurar SSL/HTTPS
- [ ] Configurar backups do banco de dados
- [ ] Monitorar logs e performance

## 🧪 Testes

```bash
# Executar todos os testes
python manage.py test

# Executar testes específicos
python manage.py test core.tests.test_views

# Executar com coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

## 🤝 Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

### Padrões de Código

- Use Black para formatação de código Python
- Siga as convenções PEP 8
- Escreva testes para novas funcionalidades
- Mantenha a documentação atualizada

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 👥 Autores

- **Pedro Henrique** - *Desenvolvimento inicial* - [@PedroHenriqueDevBR](https://github.com/PedroHenriqueDevBR)

## 🆘 Suporte

Se você encontrar algum problema ou tiver dúvidas:

1. Verifique as [Issues existentes](https://github.com/PedroHenriqueDevBR/MyDraws/issues)
2. Crie uma nova issue se necessário
3. Para suporte comercial, entre em contato: [seu-email@exemplo.com]

---

⭐ Se este projeto foi útil para você, considere dar uma estrela no GitHub!

**[📚 Documentação](https://github.com/PedroHenriqueDevBR/MyDraws)** | **[🐛 Report Bug](https://github.com/PedroHenriqueDevBR/MyDraws/issues)**
