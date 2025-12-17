"""
Azure OpenAI GPT-5.1-mini client wrapper.

Handles authentication, rate limiting, and structured output for donor prospecting.
"""

import os
import json
import time
from typing import Dict, Any, Optional, Type
from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

load_dotenv(override=True)

class AzureGPT5MiniClient:
    """Wrapper for Azure OpenAI GPT-5.1-mini with structured output support."""

    def __init__(self):
        """Initialize Azure OpenAI client."""
        self.api_key = os.environ.get("AZURE_APIKEY")
        endpoint_url = os.environ.get("AZURE_5.1_MINI_ENDPOINT")

        if not self.api_key or not endpoint_url:
            raise ValueError("AZURE_APIKEY and AZURE_5.1_MINI_ENDPOINT must be set in .env")

        # Parse endpoint to extract base URL and api_version
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(endpoint_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.deployment_name = parsed.path.split('/')[3]
        api_version = parse_qs(parsed.query).get('api-version', ['2024-05-01-preview'])[0]

        self.client = AzureOpenAI(
            azure_endpoint=base_url,
            api_key=self.api_key,
            api_version=api_version
        )

        # Rate limiting (5000 requests/min = 83 requests/sec)
        self.min_request_interval = 0.012  # ~83 req/sec max
        self.last_request_time = 0

        # Token tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0

    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()

    def chat_completion(
        self,
        messages: list[Dict[str, str]],
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_format: Optional response format for structured output
                Example: {"type": "json_schema", "json_schema": {...}}

        Returns:
            Dict with response data including 'content', 'usage', etc.
        """
        self._wait_for_rate_limit()

        params = {
            "model": self.deployment_name,
            "messages": messages
        }

        # Add response_format if provided (for structured output)
        if response_format:
            params["response_format"] = response_format

        # Note: gpt-5-mini only supports temperature=1 (default)
        # Do not set temperature parameter

        response = self.client.chat.completions.create(**params)

        # Track usage
        self.total_prompt_tokens += response.usage.prompt_tokens
        self.total_completion_tokens += response.usage.completion_tokens
        self.total_requests += 1

        return {
            "content": response.choices[0].message.content,
            "finish_reason": response.choices[0].finish_reason,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            "model": response.model
        }

    def _add_additional_properties(self, schema: dict) -> dict:
        """Recursively add additionalProperties: false to all objects in schema."""
        if isinstance(schema, dict):
            # Add to this level if it's an object
            if schema.get("type") == "object" and "additionalProperties" not in schema:
                schema["additionalProperties"] = False

            # Recurse into nested structures
            for key, value in schema.items():
                if key == "properties" and isinstance(value, dict):
                    for prop_value in value.values():
                        self._add_additional_properties(prop_value)
                elif key == "$defs" and isinstance(value, dict):
                    for def_value in value.values():
                        self._add_additional_properties(def_value)
                elif isinstance(value, dict):
                    self._add_additional_properties(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._add_additional_properties(item)

        return schema

    def structured_completion(
        self,
        messages: list[Dict[str, str]],
        response_model: Type[BaseModel],
        strict: bool = True,
        fallback_on_error: bool = True
    ) -> BaseModel:
        """
        Make a chat completion request with structured JSON output.

        Args:
            messages: List of message dicts
            response_model: Pydantic model class for response structure
            strict: Whether to use strict schema validation
            fallback_on_error: If strict fails, retry with json_object mode

        Returns:
            Instance of response_model with parsed response
        """
        try:
            schema = response_model.model_json_schema()

            # Add additionalProperties: false for strict mode (recursively)
            if strict:
                schema = self._add_additional_properties(schema)

            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__.lower(),
                    "strict": strict,
                    "schema": schema
                }
            }

            result = self.chat_completion(messages, response_format)

            # Parse JSON and validate against Pydantic model
            data = json.loads(result["content"])
            return response_model(**data)

        except Exception as e:
            if fallback_on_error and strict:
                # Fallback to json_object mode (less strict)
                print(f"  ⚠️  Strict mode failed ({str(e)[:50]}...), retrying with json_object mode")

                # Add instruction to follow schema
                messages_with_schema = messages.copy()
                messages_with_schema.append({
                    "role": "system",
                    "content": f"Return valid JSON matching this Pydantic schema: {response_model.__name__}"
                })

                response_format = {"type": "json_object"}
                result = self.chat_completion(messages_with_schema, response_format)

                # Parse and validate
                data = json.loads(result["content"])
                return response_model(**data)
            else:
                raise

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get summary of API usage."""
        return {
            "total_requests": self.total_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "estimated_cost_usd": self._estimate_cost()
        }

    def _estimate_cost(self) -> float:
        """Estimate cost based on token usage."""
        # GPT-5-mini pricing (estimate - verify actual pricing)
        # Assuming similar to GPT-4o-mini: ~$0.15/1M input, ~$0.60/1M output
        input_cost = (self.total_prompt_tokens / 1_000_000) * 0.15
        output_cost = (self.total_completion_tokens / 1_000_000) * 0.60
        return input_cost + output_cost

    def print_usage(self):
        """Print usage summary to console."""
        summary = self.get_usage_summary()
        print("\n" + "=" * 80)
        print("AZURE GPT-5.1-MINI USAGE SUMMARY")
        print("=" * 80)
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Prompt Tokens: {summary['total_prompt_tokens']:,}")
        print(f"Completion Tokens: {summary['total_completion_tokens']:,}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Estimated Cost: ${summary['estimated_cost_usd']:.4f}")
        print("=" * 80 + "\n")
