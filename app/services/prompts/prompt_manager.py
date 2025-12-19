"""Prompt management system for custom AI prompts.

Allows users to create, edit, and manage custom prompts for document analysis.
Includes storage and retrieval of user prompts.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PromptTemplate:
    """Represents a prompt template.
    
    Attributes:
        name: Prompt name
        system_prompt: System-level instructions
        user_prompt_template: User prompt with placeholders
        description: What this prompt does
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    
    def __init__(
        self,
        name: str,
        system_prompt: str,
        user_prompt_template: str,
        description: str = "",
    ) -> None:
        """Initialize prompt template.
        
        Args:
            name: Prompt identifier
            system_prompt: System instructions
            user_prompt_template: User prompt
            description: Description of what prompt does
        """
        self.name = name
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage.
        
        Returns:
            Dict: Prompt data
        """
        return {
            "name": self.name,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "PromptTemplate":
        """Create from dictionary.
        
        Args:
            data: Prompt data
            
        Returns:
            PromptTemplate: New instance
        """
        prompt = cls(
            name=data["name"],
            system_prompt=data["system_prompt"],
            user_prompt_template=data["user_prompt_template"],
            description=data.get("description", ""),
        )
        prompt.created_at = data.get("created_at", prompt.created_at)
        prompt.updated_at = data.get("updated_at", prompt.updated_at)
        return prompt


class PromptManager:
    """Manages user and system prompts.
    
    Provides:
    - Storage and retrieval of custom prompts
    - System default prompts
    - User-specific prompt management
    - Prompt validation
    """
    
    # Default system prompts - ALL IN RUSSIAN
    DEFAULT_PROMPTS = {
        "default": PromptTemplate(
            name="default",
            system_prompt=(
                "Ты эксперт по анализу документов. Твоя задача - анализировать документы "
                "и предоставлять чёткие, практичные insights. "
                "Будь кратким, но тщательным. Структурируй ответ так:\n"
                "1. Краткое резюме\n"
                "2. Ключевые моменты\n"
                "3. Важные детали\n"
                "4. Рекомендации (если применимо)"
            ),
            user_prompt_template="Проанализируй этот документ и дай ключевые выводы:",
            description="📄 Базовый анализ документа",
        ),
        "summarize": PromptTemplate(
            name="summarize",
            system_prompt=(
                "Ты эксперт по краткому изложению. "
                "Создавай чёткие, исчерпывающие резюме, которые передают суть "
                "документов минимальным текстом."
            ),
            user_prompt_template="Создай краткое резюме этого документа:",
            description="📝 Краткое резюме",
        ),
        "extract_entities": PromptTemplate(
            name="extract_entities",
            system_prompt=(
                "Ты эксперт по извлечению структурированной информации из документов. "
                "Находи и перечисляй важные сущности и связи."
            ),
            user_prompt_template=(
                "Извлеки и перечисли все важные сущности из этого документа:\n"
                "- Люди (имена, роли)\n"
                "- Организации\n"
                "- Даты\n"
                "- Числа/суммы\n"
                "- Технические термины\n"
                "- Ключевые концепции"
            ),
            description="🔍 Извлечение данных",
        ),
        "risk_analysis": PromptTemplate(
            name="risk_analysis",
            system_prompt=(
                "Ты специалист по управлению рисками. "
                "Находи потенциальные риски, проблемы и зоны внимания в документах."
            ),
            user_prompt_template=(
                "Проанализируй этот документ и определи:\n"
                "1. Потенциальные риски или проблемы\n"
                "2. Зоны внимания\n"
                "3. Недостающую информацию\n"
                "4. Несоответствия\n"
                "5. Рекомендации по снижению рисков"
            ),
            description="⚠️ Анализ рисков",
        ),
        "legal_review": PromptTemplate(
            name="legal_review",
            system_prompt=(
                "Ты опытный юридический аналитик. "
                "Проверяй документы на юридические последствия, вопросы соответствия "
                "и договорные обязательства."
            ),
            user_prompt_template=(
                "Проведи юридическую проверку этого документа, сосредоточься на:\n"
                "1. Юридические обязательства и ответственность\n"
                "2. Вопросы соответствия\n"
                "3. Ключевые договорные условия\n"
                "4. Снижение рисков\n"
                "5. Рекомендации"
            ),
            description="⚖️ Юридическая проверка",
        ),
    }
    
    def __init__(self, storage_dir: Path = Path("./data/prompts")) -> None:
        """Initialize prompt manager.
        
        Args:
            storage_dir: Directory for storing user prompts
        """
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.user_prompts: Dict[int, Dict[str, PromptTemplate]] = {}
        logger.info(f"PromptManager initialized (storage: {storage_dir})")
    
    def get_prompt(
        self,
        user_id: int,
        prompt_name: str,
    ) -> Optional[PromptTemplate]:
        """Get prompt by name.
        
        Checks user prompts first, then defaults.
        
        Args:
            user_id: Telegram user ID
            prompt_name: Prompt name
            
        Returns:
            PromptTemplate or None if not found
        """
        # Check user prompts
        if user_id in self.user_prompts:
            if prompt_name in self.user_prompts[user_id]:
                return self.user_prompts[user_id][prompt_name]
        
        # Check defaults
        return self.DEFAULT_PROMPTS.get(prompt_name)
    
    def save_prompt(
        self,
        user_id: int,
        prompt_name: str,
        system_prompt: str,
        user_prompt_template: str,
        description: str = "",
    ) -> PromptTemplate:
        """Save user prompt.
        
        Args:
            user_id: Telegram user ID
            prompt_name: Prompt name
            system_prompt: System instructions
            user_prompt_template: User prompt
            description: Prompt description
            
        Returns:
            PromptTemplate: Saved prompt
        """
        if user_id not in self.user_prompts:
            self.user_prompts[user_id] = {}
        
        prompt = PromptTemplate(
            name=prompt_name,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
            description=description,
        )
        
        self.user_prompts[user_id][prompt_name] = prompt
        
        # Persist to disk
        self._save_user_prompts(user_id)
        
        logger.info(f"Saved prompt '{prompt_name}' for user {user_id}")
        return prompt
    
    def update_prompt(
        self,
        user_id: int,
        prompt_name: str,
        system_prompt: Optional[str] = None,
        user_prompt_template: Optional[str] = None,
    ) -> bool:
        """Update existing prompt.
        
        Args:
            user_id: User ID
            prompt_name: Prompt name
            system_prompt: New system prompt (optional)
            user_prompt_template: New user prompt (optional)
            
        Returns:
            bool: True if updated, False if not found
        """
        prompt = self.get_prompt(user_id, prompt_name)
        if not prompt:
            return False
        
        # Update fields
        if system_prompt:
            prompt.system_prompt = system_prompt
        if user_prompt_template:
            prompt.user_prompt_template = user_prompt_template
        
        prompt.updated_at = datetime.now().isoformat()
        
        # Save updated prompt
        if user_id not in self.user_prompts:
            self.user_prompts[user_id] = {}
        
        self.user_prompts[user_id][prompt_name] = prompt
        self._save_user_prompts(user_id)
        
        logger.info(f"Updated prompt '{prompt_name}' for user {user_id}")
        return True
    
    def delete_prompt(
        self,
        user_id: int,
        prompt_name: str,
    ) -> bool:
        """Delete user prompt.
        
        Args:
            user_id: User ID
            prompt_name: Prompt name
            
        Returns:
            bool: True if deleted, False if not found
        """
        if user_id in self.user_prompts and prompt_name in self.user_prompts[user_id]:
            del self.user_prompts[user_id][prompt_name]
            self._save_user_prompts(user_id)
            logger.info(f"Deleted prompt '{prompt_name}' for user {user_id}")
            return True
        return False
    
    def list_prompts(self, user_id: int) -> Dict[str, PromptTemplate]:
        """List all available prompts for user.
        
        Includes both user prompts and defaults.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: Available prompts {name: template}
        """
        all_prompts = dict(self.DEFAULT_PROMPTS)
        
        if user_id in self.user_prompts:
            all_prompts.update(self.user_prompts[user_id])
        
        return all_prompts
    
    def get_user_prompts(self, user_id: int) -> Dict[str, PromptTemplate]:
        """Get only user-created prompts.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict: User prompts
        """
        return self.user_prompts.get(user_id, {})
    
    def load_user_prompts(self, user_id: int) -> None:
        """Load user prompts from disk.
        
        Args:
            user_id: User ID
        """
        user_file = self.storage_dir / f"user_{user_id}.json"
        
        if not user_file.exists():
            return
        
        try:
            with open(user_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.user_prompts[user_id] = {
                name: PromptTemplate.from_dict(prompt_data)
                for name, prompt_data in data.items()
            }
            logger.info(f"Loaded {len(self.user_prompts[user_id])} prompts for user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to load prompts for user {user_id}: {e}")
    
    def _save_user_prompts(self, user_id: int) -> None:
        """Save user prompts to disk.
        
        Args:
            user_id: User ID
        """
        if user_id not in self.user_prompts:
            return
        
        user_file = self.storage_dir / f"user_{user_id}.json"
        
        try:
            data = {
                name: prompt.to_dict()
                for name, prompt in self.user_prompts[user_id].items()
            }
            
            with open(user_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Persisted {len(data)} prompts for user {user_id}")
        
        except Exception as e:
            logger.error(f"Failed to save prompts for user {user_id}: {e}")
