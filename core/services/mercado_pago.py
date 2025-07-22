import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple

from django.db import transaction
from decouple import config

from core.models import Profile, CreditTransaction

try:
    import mercadopago
except ImportError:
    mercadopago = None

logger = logging.getLogger(__name__)


class MercadoPagoService:
    """
    Serviço para integração com o Mercado Pago
    Gerencia pagamentos e adição de créditos ao perfil do usuário
    """

    def __init__(self):
        """Inicializa o serviço com as credenciais do Mercado Pago"""
        if mercadopago is None:
            logger.error("SDK do Mercado Pago não instalado. Execute: pip install mercadopago")
            raise ImportError("SDK do Mercado Pago não encontrado")
            
        self.access_token = config("MERCADO_PAGO_ACCESS_TOKEN", default="")
        self.public_key = config("MERCADO_PAGO_PUBLIC_KEY", default="")
        
        if not self.access_token:
            logger.error("MERCADO_PAGO_ACCESS_TOKEN não encontrado nas configurações")
            raise ValueError("Token de acesso do Mercado Pago é obrigatório")
        
        # Inicializa o SDK do Mercado Pago
        self.sdk = mercadopago.SDK(self.access_token)

    def create_payment_preference(
        self, 
        profile: Profile, 
        credit_amount: int, 
        unit_price: Decimal,
        description: str = "Compra de créditos"
    ) -> Optional[Dict]:
        """
        Cria uma preferência de pagamento no Mercado Pago
        
        Args:
            profile: Perfil do usuário que está comprando
            credit_amount: Quantidade de créditos a serem comprados
            unit_price: Preço unitário por crédito
            description: Descrição do pagamento
            
        Returns:
            Dict com dados da preferência criada ou None em caso de erro
        """
        try:
            total_price = float(unit_price * credit_amount)
            
            preference_data = {
                "items": [
                    {
                        "title": f"{credit_amount} créditos - MyDraws",
                        "description": description,
                        "quantity": 1,
                        "unit_price": total_price,
                        "currency_id": "BRL"
                    }
                ],
                "payer": {
                    "name": profile.first_name or profile.username,
                    "surname": profile.last_name or "",
                    "email": profile.email,
                },
                "back_urls": {
                    "success": config("MERCADO_PAGO_SUCCESS_URL", default=""),
                    "failure": config("MERCADO_PAGO_FAILURE_URL", default=""),
                    "pending": config("MERCADO_PAGO_PENDING_URL", default=""),
                },
                "auto_return": "approved",
                "external_reference": f"user_{profile.id}_credits_{credit_amount}",
                "notification_url": config("MERCADO_PAGO_WEBHOOK_URL", default=""),
                "statement_descriptor": "MYDRAWS",
                "metadata": {
                    "user_id": profile.id,
                    "credit_amount": credit_amount,
                    "unit_price": str(unit_price)
                }
            }
            
            preference_response = self.sdk.preference().create(preference_data)
            
            if preference_response["status"] == 201:
                logger.info(
                    "Preferência criada com sucesso para usuário %s. ID: %s",
                    profile.id,
                    preference_response['response']['id']
                )
                return preference_response["response"]
            else:
                logger.error(
                    "Erro ao criar preferência: %s",
                    preference_response.get('message', 'Erro desconhecido')
                )
                return None
                
        except (ValueError, KeyError) as e:
            logger.error("Erro de dados ao criar preferência de pagamento: %s", str(e))
            return None
        except Exception as e:
            logger.error("Erro inesperado ao criar preferência de pagamento: %s", str(e))
            return None

    def process_payment_notification(self, payment_id: str) -> Tuple[bool, str]:
        """
        Processa notificação de pagamento do webhook do Mercado Pago
        
        Args:
            payment_id: ID do pagamento recebido via webhook
            
        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            # Busca informações do pagamento
            payment_response = self.sdk.payment().get(payment_id)
            
            if payment_response["status"] != 200:
                error_msg = f"Erro ao buscar pagamento {payment_id}: {payment_response.get('message', 'Erro desconhecido')}"
                logger.error(error_msg)
                return False, error_msg
            
            payment_data = payment_response["response"]
            
            # Verifica se o pagamento foi aprovado
            if payment_data["status"] != "approved":
                logger.info(
                    "Pagamento %s não aprovado. Status: %s",
                    payment_id,
                    payment_data['status']
                )
                return False, f"Pagamento não aprovado. Status: {payment_data['status']}"
            
            # Extrai dados do metadata
            metadata = payment_data.get("metadata", {})
            external_reference = payment_data.get("external_reference", "")
            
            if not metadata or not external_reference:
                error_msg = f"Dados insuficientes no pagamento {payment_id}"
                logger.error(error_msg)
                return False, error_msg
            
            user_id = metadata.get("user_id")
            credit_amount = metadata.get("credit_amount")
            
            if not user_id or not credit_amount:
                error_msg = f"Metadata inválido no pagamento {payment_id}"
                logger.error(error_msg)
                return False, error_msg
            
            # Processa o pagamento
            success, message = self._add_credits_to_user(
                user_id=int(user_id),
                credit_amount=int(credit_amount),
                payment_id=payment_id
            )
            
            return success, message
            
        except (ValueError, KeyError) as e:
            error_msg = f"Erro de dados ao processar notificação de pagamento {payment_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Erro inesperado ao processar notificação de pagamento {payment_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    @transaction.atomic
    def _add_credits_to_user(
        self, 
        user_id: int, 
        credit_amount: int, 
        payment_id: str
    ) -> Tuple[bool, str]:
        """
        Adiciona créditos ao perfil do usuário de forma atômica
        
        Args:
            user_id: ID do usuário
            credit_amount: Quantidade de créditos a adicionar
            payment_id: ID do pagamento do Mercado Pago
            
        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            # Busca o perfil do usuário
            profile = Profile.objects.get(id=user_id)
            
            # Verifica se já existe uma transação para este pagamento
            existing_transaction = CreditTransaction.objects.filter(
                profile=profile,
                transaction_type=f"MERCADO_PAGO_{payment_id}"
            ).first()
            
            if existing_transaction:
                logger.warning("Transação já processada para pagamento %s", payment_id)
                return False, "Transação já processada"
            
            # Adiciona créditos ao perfil
            profile.credit_amount += credit_amount
            profile.save()
            
            # Cria registro da transação
            CreditTransaction.objects.create(
                profile=profile,
                amount=credit_amount,
                transaction_type=f"MERCADO_PAGO_{payment_id}",
            )
            
            success_msg = (
                "Créditos adicionados com sucesso! "
                f"Usuário: {profile.username}, "
                f"Créditos: {credit_amount}, "
                f"Total: {profile.credit_amount}, "
                f"Pagamento: {payment_id}"
            )
            logger.info(success_msg)
            
            return True, success_msg
            
        except Profile.DoesNotExist:
            error_msg = f"Usuário com ID {user_id} não encontrado"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"Erro inesperado ao adicionar créditos para usuário {user_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_payment_status(self, payment_id: str) -> Optional[Dict]:
        """
        Consulta o status de um pagamento específico
        
        Args:
            payment_id: ID do pagamento
            
        Returns:
            Dict com dados do pagamento ou None em caso de erro
        """
        try:
            payment_response = self.sdk.payment().get(payment_id)
            
            if payment_response["status"] == 200:
                return payment_response["response"]
            else:
                logger.error(
                    "Erro ao consultar pagamento %s: %s",
                    payment_id,
                    payment_response.get('message', 'Erro desconhecido')
                )
                return None
                
        except Exception as e:
            logger.error("Erro ao consultar status do pagamento %s: %s", payment_id, str(e))
            return None

    def cancel_payment(self, payment_id: str) -> Tuple[bool, str]:
        """
        Cancela um pagamento
        
        Args:
            payment_id: ID do pagamento a ser cancelado
            
        Returns:
            Tuple (sucesso: bool, mensagem: str)
        """
        try:
            cancel_response = self.sdk.payment().cancel(payment_id)
            
            if cancel_response["status"] == 200:
                logger.info("Pagamento %s cancelado com sucesso", payment_id)
                return True, "Pagamento cancelado com sucesso"
            else:
                error_msg = f"Erro ao cancelar pagamento: {cancel_response.get('message', 'Erro desconhecido')}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Erro ao cancelar pagamento {payment_id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def get_available_payment_methods(self) -> Optional[Dict]:
        """
        Retorna os métodos de pagamento disponíveis
        
        Returns:
            Dict com métodos de pagamento ou None em caso de erro
        """
        try:
            methods_response = self.sdk.payment_methods().list_all()
            
            if methods_response["status"] == 200:
                return methods_response["response"]
            else:
                logger.error(
                    "Erro ao consultar métodos de pagamento: %s",
                    methods_response.get('message', 'Erro desconhecido')
                )
                return None
                
        except Exception as e:
            logger.error("Erro ao consultar métodos de pagamento: %s", str(e))
            return None

# Função auxiliar para criar instância do serviço
def get_mercado_pago_service():
    """
    Retorna uma instância do MercadoPagoService
    Útil para testes e controle de dependências
    """
    return MercadoPagoService()
