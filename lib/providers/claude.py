import json
import time
from typing import List, Dict, Optional
from .base import AIProvider


class ClaudeProvider(AIProvider):
    """Claude provider implementation via AWS Bedrock."""
    
    def __init__(self, bedrock_client):
        self.bedrock_client = bedrock_client
    
    def get_name(self) -> str:
        return "Claude 3.5 Sonnet (AWS Bedrock)"
    
    def chat(self, messages: List[Dict[str, str]], tools: List[Dict],
             retry_count: int = 0, max_retries: int = 5) -> Optional[Dict]:
        """
        Send messages to Claude via AWS Bedrock and get response with exponential backoff retry.
        
        Args:
            messages: List of message dicts with role and content
            tools: List of tool definitions
            retry_count: Current retry attempt
            max_retries: Maximum number of retries
        
        Returns:
            Response dict in OpenAI format, or None if error
        """
        try:
            # Convert OpenAI format to Claude format
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg['role'] == 'system':
                    system_message = msg['content']
                elif msg['role'] == 'tool':
                    # Convert tool response to user message
                    claude_messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": msg['tool_call_id'],
                                "content": msg['content']
                            }
                        ]
                    })
                else:
                    # Handle regular messages and tool calls
                    content = []
                    
                    if msg.get('content'):
                        content.append({"type": "text", "text": msg['content']})
                    
                    if msg.get('tool_calls'):
                        for tool_call in msg['tool_calls']:
                            content.append({
                                "type": "tool_use",
                                "id": tool_call['id'],
                                "name": tool_call['function']['name'],
                                "input": json.loads(tool_call['function']['arguments'])
                            })
                    
                    if content:
                        claude_messages.append({
                            "role": msg['role'] if msg['role'] != 'assistant' else 'assistant',
                            "content": content
                        })
            
            # Convert tools to Claude format
            claude_tools = []
            for tool in tools:
                claude_tools.append({
                    "name": tool['function']['name'],
                    "description": tool['function']['description'],
                    "input_schema": tool['function']['parameters']
                })
            
            # Call Bedrock
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": claude_messages,
                "tools": claude_tools
            }
            
            if system_message:
                request_body["system"] = system_message
            
            response = self.bedrock_client.invoke_model(
                modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Convert Claude response to OpenAI format
            openai_response = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": []
                    },
                    "finish_reason": response_body.get('stop_reason', 'stop')
                }]
            }
            
            # Extract content and tool calls
            for content_block in response_body.get('content', []):
                if content_block['type'] == 'text':
                    openai_response['choices'][0]['message']['content'] = content_block['text']
                elif content_block['type'] == 'tool_use':
                    openai_response['choices'][0]['message']['tool_calls'].append({
                        "id": content_block['id'],
                        "type": "function",
                        "function": {
                            "name": content_block['name'],
                            "arguments": json.dumps(content_block['input'])
                        }
                    })
            
            # Set finish reason
            if openai_response['choices'][0]['message']['tool_calls']:
                openai_response['choices'][0]['finish_reason'] = 'tool_calls'
            
            return openai_response
            
        except Exception as e:
            if retry_count < max_retries:
                wait_time = 2 ** retry_count
                print(f"⏳ Error: {e}. Retrying in {wait_time}s... (attempt {retry_count + 1}/{max_retries})")
                time.sleep(wait_time)
                return self.chat(messages, tools, retry_count + 1, max_retries)
            else:
                print(f"Error calling Bedrock: {e}")
                return None
