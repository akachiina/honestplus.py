# honestplus.py

<div align="center">
  <b>🌐 Idioma</b>
  <table>
    <tr>
      <td align="center"><a href="README.md">🇺🇸 English</a></td>
      <td align="center"><a href="README.pt-BR.md">🇧🇷 Português</a></td>
    </tr>
  </table>
</div>

---

> [!CAUTION]
> Este projeto é para fins **educacionais apenas**. O autor não se responsabiliza por qualquer uso indevido, violação dos Termos de Serviço ou danos decorrentes do uso desta biblioteca. Use por sua conta e risco.

## Sumário

- [Sobre](#sobre)
- [Instalação](#instalação)
- [Início Rápido](#início-rápido)
- [Obtendo o Token](#obtendo-o-token)
- [Exemplos de Uso](#exemplos-de-uso)
  - [Criação de Conta](#criação-de-conta)
  - [Criando um Post](#criando-um-post)
  - [Enquetes](#enquetes)
  - [Lendo o Feed](#lendo-o-feed)
  - [Comentários](#comentários)
  - [Stories](#stories-1)
  - [Chats e Mensagens](#chats-e-mensagens)
  - [Perfil](#perfil)
  - [Seguir / Deixar de Seguir](#seguir--deixar-de-seguir)
  - [Busca](#busca)
  - [Perguntas](#perguntas)
  - [Bloquear / Silenciar](#bloquear--silenciar)
  - [Denúncias](#denúncias)
- [Sistema de Eventos](#sistema-de-eventos)
- [Referência da API](#referência-da-api)
- [Requisitos](#requisitos)
- [Licença](#licença)
- [Aviso](#aviso)

## Sobre

Wrapper não oficial e assíncrono em Python para a API do [Honest+](https://honest.plus), inspirado na filosofia de design do discord.py.

## Funcionalidades

- **Sintaxe async/await** — Construída sobre `aiohttp` para operações assíncronas eficientes
- **Arquitetura baseada em eventos** — Reaja a eventos em tempo real (notificações, mensagens)
- **Cobertura completa da API** — Posts, comentários, stories, chats, enquetes, perguntas e mais
- **Processamento de imagens** — Utilitários para preparar imagens de stories (1037×1843)
- **Renderização de texto** — Crie stories de texto e sobreposições com a fonte Fredoka inclusa
- **Type hints** — Suporte completo a tipagem para melhor integração com IDEs

## Instalação

```bash
pip install git+https://github.com/akachiina/honestplus.py.git
```

As dependências (`aiohttp` e `Pillow`) são instaladas automaticamente.

## Início Rápido

```python
import honestplus
import asyncio

# language seleciona o servidor de conteúdo: "en" (padrão), "pt" (Brasil), "es" (Espanhol), etc.
client = honestplus.Client(token="seu_token_jwt", language="pt")

@client.event
async def on_ready():
    print(f"Conectado como {client.user.name} (@{client.user.nick})")

async def main():
    await client.start()

asyncio.run(main())
```

## Exemplos de Uso

### Criação de Conta

```python
import honestplus
from honestplus import Client, Gender

async with Client() as client:
    # Passo 1: Tentar login com Google
    result = await client.login_google(
        google_token="token_jwt_google_oauth",
        device_id="identificador_dispositivo",
    )

    if result.not_found:
        # Conta não existe — API sugeriu um nick
        print(f"Nick sugerido: {result.nick}")

        # Passo 2: Verificar se o nick está disponível
        available = await client.check_nick("meunick")

        # Passo 3: Registrar a nova conta
        user = await client.register_google(
            google_token="token_jwt_google_oauth",
            device_id="identificador_dispositivo",
            name="Meu Nome",
            nick="meunick",
            gender=Gender.MAN.value,
            birthday="2000-01-15T00:00:00.000",
        )
    else:
        # Conta existe — já está logado
        print(f"Bem-vindo de volta, {result.user.name}!")

    # Passo 4: Buscar interesses disponíveis e configurar perfil
    interests = await client.get_interests()
    await client.update_profile(interests=["politics", "music"])

    # Passo 5: Descobrir usuários com interesses similares
    users = await client.discover_users()
    for u in users:
        print(f"{u.name} (@{u.nick})")
```

### Criando um Post

```python
post = await client.create_post(
    text="Olá do honestplus.py!",
    visibility=honestplus.PostVisibility.PUBLIC,
)
```

### Enquetes

```python
post = await client.create_poll_post(
    text="Qual sua cor favorita?",
    options=["Vermelho", "Azul", "Verde"],
    is_anonymous=True,
    allows_multiple=False,
)

# Votar na enquete
await client.vote_poll(post.uuid, [option_uuid])
```

### Lendo o Feed

```python
# Feed geral
async for post in client.get_feed(limit=20):
    print(f"{post.user.name}: {post.text}")
    print(f"  ↑{post.likes} ↓{post.dislikes} 💬{post.comments}")

# Feed só de amigos
async for post in client.get_friends_feed(limit=10):
    print(post.text)

# Feed de quem você segue
async for post in client.get_following_feed(limit=10):
    print(post.text)
```

### Comentários

```python
# Adicionar um comentário
comment = await post.comment("Bom post!")

# Responder a um comentário
reply = await post.comment("Concordo!", reply_id=comment.uuid)

# Buscar todos os comentários
comments = await post.get_comments()
for c in comments:
    print(f"{c.user.name}: {c.text}")

# Reagir a um comentário
await comment.like()
await comment.dislike()
await comment.remove_reaction()
```

### Stories

```python
# Fazer upload de uma imagem e criar story (preparado automaticamente para 1037×1843)
media_uuid = await client.upload_photo("foto.jpg", media_type="story")
await client.wait_for_media(media_uuid)
story = await client.create_story(media_uuid)

# Criar story de texto
text_image = honestplus.create_text_story(
    "Olá mundo!",
    background_color="#1a1a2e",
    text_color="white",
    font_size=70,
)
media_uuid = await client.upload_photo(text_image, media_type="story")
await client.wait_for_media(media_uuid)
story = await client.create_story(media_uuid)

# Adicionar texto sobre uma imagem
overlay = honestplus.add_text_to_image(
    "foto.jpg",
    "Confira isso!",
    text_color="white",
    font_size=80,
)

# Ver stories do feed
stories = client.get_story_feed()
for story in stories:
    print(f"{story.user.name} postou um story")
    await story.view()
    await story.like()
```

### Chats e Mensagens

```python
# Listar todos os chats
chats = await client.get_chats()
for chat in chats:
    print(f"Chat com {chat.user.name}: {chat.last_message_text}")

# Abrir chat com um usuário
chat = await client.get_chat_by_user("user_uuid")

# Enviar mensagens
await chat.send("Olá!")
await chat.send_photo("foto.jpg")

# Histórico do chat
messages = await chat.get_history(limit=50)
for msg in messages:
    print(f"{msg.user.name}: {msg.text}")

# Indicador de digitando
await chat.typing()
```

### Perfil

```python
# Ver perfil de um usuário
profile = await client.get_profile("username")
print(f"{profile.user.name} — {profile.followers} seguidores")
print(f"Bio: {profile.description}")
print(f"Seguindo: {profile.following}")

# Atualizar seu próprio perfil
await client.update_profile(
    name="Novo Nome",
    description="Minha nova bio",
    photo="photo_uuid",
    header="header_uuid",
    interests=["programação", "música"],
)

# Upload de nova foto de perfil
photo_uuid = await client.upload_photo("selfie.jpg", media_type="profile")
await client.wait_for_media(photo_uuid)
await client.update_profile(photo=photo_uuid)
```

### Seguir / Deixar de Seguir

```python
await client.follow_user("user_uuid")
await client.unfollow_user("user_uuid")

# Ver seguidores e seguindo
followers = await client.get_followers("user_uuid", page=0)
following = await client.get_following("user_uuid", page=0)
```

### Busca

```python
users = await client.search_users("busca", limit=10)
for user in users:
    print(f"{user.name} (@{user.nick})")

posts = await client.search_posts("busca", limit=10)
for post in posts:
    print(f"{post.user.name}: {post.text}")
```

### Perguntas

```python
# Enviar uma pergunta
await client.send_question(
    text="Qual sua comida favorita?",
    category="personal",
    anonymous=True,
)

# Receber perguntas
async for question in client.get_questions_received(limit=10):
    print(f"P: {question.text} (de {question.user.name})")

# Responder uma pergunta
await question.answer("Pizza!")
```

### Bloquear / Silenciar

```python
await client.block_user("user_uuid")
await client.unblock_user("block_id")

await client.mute_user("user_uuid")
await client.unmute_user("user_uuid")

blocked = await client.get_blocked_users()
```

### Denúncias

```python
await client.report_post("post_uuid", "Spam")
await client.report_user("user_uuid", "Assédio")
await client.report_comment("post_uuid", "comment_uuid", "Inadequado")
```

## Sistema de Eventos

```python
@client.event
async def on_ready():
    """Chamado quando o cliente conecta e está pronto."""
    print("Bot pronto!")

@client.event
async def on_notification(notification):
    """Chamado quando uma nova notificação é recebida."""
    print(f"Nova notificação: {notification.type}")

@client.event
async def on_follow(user):
    """Chamado quando alguém te segue."""
    print(f"Novo seguidor: {user.name}")

@client.event
async def on_comment(notification):
    """Chamado quando alguém comenta no seu post."""
    print(f"Novo comentário de {notification.user.name}")
```

Inicie o polling com `await client.start(poll_interval=15.0)`.

## Autenticação

### Token JWT (recomendado)

A única forma prática de usar esta biblioteca. Passe o token diretamente ao criar o client:

```python
client = honestplus.Client(token="seu_token_jwt")
```

Para obter o token:

1. Instale um emulador Android com acesso root no seu PC
2. Instale o [HTTP Toolkit](https://httptoolkit.com/) para interceptar o tráfego HTTP
3. Abra o app Honest+ no emulador
4. Capture as requisições e copie o valor do header `Authorization: Bearer <token>`

> [!CAUTION]
> Trate seu token como um segredo. Não o compartilhe publicamente.

### Google / Facebook OAuth (apenas para referência)

Os métodos `login_google()`, `register_google()` e `login_facebook()` existem na biblioteca porque a API os suporta, mas **não podem ser usados** a partir daqui. O fluxo OAuth requer o client ID do Google/Facebook configurado no app Android do Honest+, que está vinculado à chave de assinatura do app e não pode ser replicado externamente. Esses métodos são mantidos apenas para completude da API.

## Referência da API

### Client

| Método | Retorna | Descrição |
|---|---|---|
| `login_google(google_token, device_id, name)` | `LoginResult` | Login com Google OAuth (retorna `logged` ou `notFound`) |
| `register_google(google_token, device_id, name, nick, ...)` | `User` | Registrar nova conta com Google OAuth |
| `login_facebook(facebook_token, device_id, name)` | `User` | Login com Facebook OAuth |
| `check_nick(nick)` | `bool` | Verificar se um nick está disponível |
| `get_interests()` | `dict` | Buscar interesses disponíveis e selecionados |
| `logout()` | `None` | Encerrar sessão |
| `get_profile(nick)` | `Profile` | Ver perfil de um usuário |
| `get_user_config()` | `dict` | Ver configurações (notificações, privacidade, etc.) |
| `update_user_config(...)` | `None` | Atualizar configurações do usuário |
| `update_profile(...)` | `None` | Atualizar seu perfil |
| `create_post(text, visibility, post_type)` | `Post` | Criar um novo post |
| `get_post(post_uuid)` | `Post` | Buscar um post por UUID |
| `get_feed(limit)` | `AsyncIterator[Post]` | Feed geral |
| `get_friends_feed(limit)` | `AsyncIterator[Post]` | Feed de amigos |
| `get_following_feed(limit)` | `AsyncIterator[Post]` | Feed de quem você segue |
| `search_posts(query, limit)` | `List[Post]` | Buscar posts |
| `follow_post(post_uuid)` | `None` | Seguir um post (receber notificações de comentários) |
| `unfollow_post(post_uuid)` | `None` | Deixar de seguir um post |
| `upload_photo(file_path, media_type)` | `str` | Upload de mídia, retorna UUID |
| `add_to_gallery(media_uuid)` | `None` | Adicionar foto à galeria do perfil |
| `create_story(media_uuid, items)` | `Story` | Criar um story |
| `get_story_feed()` | `List[Story]` | Feed de stories |
| `get_chats()` | `List[Chat]` | Listar todos os chats |
| `get_chat_by_user(user_uuid)` | `Chat` | Abrir chat com usuário |
| `get_notification_resume()` | `NotificationResume` | Contagem de não lidos |
| `get_notifications(limit)` | `AsyncIterator[Notification]` | Todas as notificações |
| `search_users(query, limit)` | `List[User]` | Buscar usuários |
| `send_question(text, category, anonymous)` | `None` | Enviar uma pergunta |
| `delete_profile_data(posts, comments, stories)` | `None` | Deletar posts/comentários/stories em massa |
| `delete_account()` | `None` | Deletar conta permanentemente |
| `discover_users()` | `List[User]` | Sugestões de usuários no Discover |
| `discover_questions()` | `List[dict]` | Perguntas em alta no Discover |
| `discover_stories()` | `List[Story]` | Stories populares no Discover |

### Models

| Model | Atributos Principais |
|---|---|
| `User` | `uuid`, `name`, `nick`, `profile_photo`, `profile_photo_url` |
| `Profile` | `user`, `description`, `followers`, `following`, `is_following`, `interests` |
| `Post` | `uuid`, `user`, `text`, `type`, `likes`, `dislikes`, `comments`, `media_url` |
| `Comment` | `uuid`, `user`, `text`, `likes`, `dislikes`, `reply_to_uuid` |
| `Story` | `uuid`, `user`, `items`, `liked`, `media_url` |
| `Chat` | `uuid`, `user`, `last_message`, `unread_count` |
| `Message` | `id`, `user`, `type`, `text`, `media`, `date` |
| `Notification` | `uuid`, `user`, `type`, `action`, `is_read` |
| `Question` | `uuid`, `user`, `text`, `answer`, `is_anonymous`, `is_answered` |

### Enums

| Enum | Valores |
|---|---|
| `ReactionType` | `LIKE`, `DISLIKE`, `NEUTRAL` |
| `PostVisibility` | `PUBLIC`, `PRIVATE`, `FOLLOWERS` |
| `MediaType` | `PROFILE`, `HEADER`, `CHAT`, `STORY`, `POST`, `FOTO` |
| `Gender` | `MAN`, `WOMAN`, `OTHER` |
| `NotificationType` | `FOLLOW`, `COMMENT`, `REPLY`, `MENTION`, `POST_REACTION`, `QUESTION`, `ANSWER`, `CHAT_MESSAGE` |

### Exceções

| Exceção | Quando |
|---|---|
| `HonestException` | Exceção base |
| `AuthenticationError` | Token inválido ou expirado |
| `NotFoundError` | Recurso não encontrado (404) |
| `RateLimitError` | Limite de requisições excedido |
| `APIError` | Erro geral da API |
| `ValidationError` | Falha na validação de entrada |
| `MediaProcessingError` | Falha no upload/processamento de mídia |

## Requisitos

- Python 3.8+
- `aiohttp`
- `Pillow`

## Licença

Licença MIT.

## Aviso

Esta biblioteca não é oficialmente afiliada ou endossada pelo Honest+. É um projeto independente criado para fins educacionais e de desenvolvimento.
