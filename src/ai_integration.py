"""Integration module for AI services."""

from typing import Dict, Any, Optional, List
import os


class AIIntegration:
    """Handle integration with AI services."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('AI_MODEL', 'gpt-4')
        self.temperature = float(os.getenv('AI_TEMPERATURE', '0.3'))
    
    def analyze_code(self, code: str, context: str = "") -> Dict[str, Any]:
        """Analyze code using AI."""
        if not self.api_key:
            return {'error': 'No API key provided'}
        
        # This would call OpenAI API in production
        return {
            'summary': 'Code analysis complete',
            'suggestions': [],
            'score': 85
        }
    
    def explain_issue(self, issue: Dict[str, Any]) -> str:
        """Get AI explanation of an issue."""
        if not self.api_key:
            return "AI explanation unavailable"
        
        return f"Issue: {issue.get('message', 'Unknown')}\n\nRecommendation: Review and fix this issue."
    
    def generate_summary(self, issues: List[Dict[str, Any]]) -> str:
        """Generate AI summary of issues."""
        if not self.api_key:
            return "AI summary unavailable"
        
        critical = sum(1 for i in issues if i.get('severity') == 'critical')
        warnings = sum(1 for i in issues if i.get('severity') == 'warning')
        
        return f"Found {critical} critical issues and {warnings} warnings. Overall code quality needs attention."
    
    def suggest_fixes(self, code: str, issue: str) -> List[str]:
        """Suggest fixes for an issue."""
        return [
            "Consider refactoring this section",
            "Add proper error handling",
            "Review for security implications"
        ]


class OpenAIIntegration(AIIntegration):
    """OpenAI-specific integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.client = None
    
    def _init_client(self):
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            pass
    
    def analyze_code(self, code: str, context: str = "") -> Dict[str, Any]:
        """Analyze code using OpenAI."""
        if not self.client:
            self._init_client()
        
        if not self.client:
            return {'error': 'OpenAI client not available'}
        
        prompt = f"""Analyze this code and provide feedback:
        
Context: {context}

Code:
{code}

Provide a brief analysis including:
1. Potential bugs
2. Security concerns
3. Code quality issues
4. Suggested improvements
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            )
            return {
                'analysis': response.choices[0].message.content,
                'model': self.model
            }
        except Exception as e:
            return {'error': str(e)}


class AnthropicIntegration(AIIntegration):
    """Anthropic Claude integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.client = None
    
    def _init_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            pass
    
    def analyze_code(self, code: str, context: str = "") -> Dict[str, Any]:
        """Analyze code using Claude."""
        if not self.client:
            self._init_client()
        
        if not self.client:
            return {'error': 'Anthropic client not available'}
        
        return {
            'analysis': 'Claude analysis placeholder',
            'model': 'claude-3'
        }


def get_ai_provider(provider: str = 'openai', api_key: Optional[str] = None) -> AIIntegration:
    """Get AI provider instance."""
    providers = {
        'openai': OpenAIIntegration,
        'anthropic': AnthropicIntegration
    }
    
    provider_class = providers.get(provider.lower(), OpenAIIntegration)
    return provider_class(api_key)