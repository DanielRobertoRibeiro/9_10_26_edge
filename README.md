# 🌐 FIWARE Edge Provisioner - Checkpoint Prep (23/10)

Repositório dedicado à arquitetura de **Edge Computing e FIWARE**, focado na automação de provisionamento de dispositivos IoT e serviços para a entrega do Checkpoint (CP) em **23 de outubro**.

## 🚀 Sobre o Projeto

Este projeto utiliza um script em Python para realizar o provisionamento automatizado no ecossistema FIWARE (como Orion Context Broker e IoT Agent), registrando serviços (`Service`), grupos e dispositivos (`Devices`) de forma rápida e padronizada.

## 🛠️ Tecnologias Utilizadas

* **Python 3.x**
* **FIWARE Ecosystem** (Orion Context Broker, IoT Agent)
* **Docker & Docker Compose** (para o ambiente de infraestrutura edge/cloud)
* **Bibliotecas Python:** `requests` (ou equivalentes para requisições HTTP)

## 📋 Pré-requisitos

Antes de executar o script de provisionamento, certifique-se de que você possui:

* Python 3.8+ instalado em sua máquina.
* O ecossistema FIWARE rodando (via Docker Compose na sua máquina local ou em um servidor remoto).
* As dependências do Python instaladas.

## 📦 Instalação e Configuração

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/DanielRobertoRibeiro/9_10_26_edge.git
   cd 9_10_26_edge
   ```

2. **Instale as dependências necessárias:**
   ```bash
   pip install requests
   ```
   *(Caso exista um arquivo `requirements.txt`, execute: `pip install -r requirements.txt`)*

3. **Verifique as variáveis de configuração:**
   Certifique-se de que os endpoints do FIWARE (Orion e IoT Agent) configurados dentro do script `fiware_provisioner.py` apontam corretamente para o seu ambiente (ex: `http://localhost:1026` para o Orion e `http://localhost:4041` para o IoT Agent).

## ▶️ Como Executar o Provisionador

Para realizar o cadastro e provisionamento automático dos dispositivos IoT no FIWARE, execute o script principal na raiz do repositório:

```bash
python ./fiware_provisioner.py
```

### O que o script faz:
* Configura os headers de serviço (`fiware-service` e `fiware-servicepath`).
* Registra o serviço no IoT Agent.
* Envia o payload de cadastro dos dispositivos com seus respectivos atributos (sensores/atuadores).

## 🧪 Testando o Ambiente para o CP

1. **Valide o Orion Context Broker:**
   Faça uma requisição GET para listar as entidades cadastradas:
   ```bash
   curl -X GET "http://localhost:1026/v2/entities" -H "fiware-service: seu_service" -H "fiware-servicepath: /"
   ```

2. **Simule telemetria:**
   Garanta que os dados enviados pelos dispositivos chegam corretamente ao broker antes da avaliação.

## 📅 Checklist para o Checkpoint (23/10)

* [ ] Infraestrutura Docker rodando sem erros.
* [ ] Script `fiware_provisioner.py` executando com sucesso (retornando status HTTP 201/204).
* [ ] Entidades visíveis no Orion Context Broker.
* [ ] Documentação e prints de validação salvos.

## 📄 Licença

Projeto desenvolvido para fins acadêmicos e avaliativos.
