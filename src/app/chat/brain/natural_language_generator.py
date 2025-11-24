from __future__ import annotations

"""
Natural Language Generator: Uses LLM to create narrative responses from structured data.

Follows LLD principles:
- Single Responsibility: focused on NL generation from tool results
- Dependency Inversion: depends on OpenAI client abstraction
- Open/Closed: extensible via prompt templates and query type handlers
"""

import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .openai_client import get_openai_client
from .config import BrainConfig
from .logger import log_call, log_data_flow


@dataclass(frozen=True)
class NLGContext:
    """Context for natural language generation."""
    user_role: str
    user_question: str
    tool_name: str
    tool_args: Dict[str, Any]
    data_summary: Dict[str, Any]  # Condensed data stats for LLM
    raw_data_available: bool = True


class NaturalLanguageGenerator:
    """Generate natural language responses from structured tool results."""
    
    @log_data_flow("nlg.should_use_nlg")
    def should_use_nlg(self, tool_name: str, user_question: str, data_size: int) -> bool:
        """Always enable NLG; downstream prompt rules enforce brevity and accuracy."""
        return True
    
    @log_data_flow("nlg.generate_response")
    def generate_response(self, context: NLGContext) -> Optional[str]:
        """Generate natural language response using LLM."""
        client = get_openai_client()
        if not client:
            return None
        
        prompt = self._build_prompt(context)
        if not prompt:
            return None
        
        try:
            cfg = BrainConfig.from_env()
            response = client.chat.completions.create(
                model=cfg.openai_model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=max(0.0, min(1.0, cfg.llm_temperature)) or 0.3,
                max_tokens=cfg.llm_max_tokens or 300,
            )
            
            return response.choices[0].message.content.strip()
        except Exception:
            # Graceful degradation - return None to fall back to template
            return None
    
    @log_data_flow("nlg.generate_unified_response")
    def generate_unified_response(self, context: NLGContext) -> Optional[str]:
        """Generate unified response using comprehensive prompt that handles all scenarios."""
        client = get_openai_client()
        if not client:
            return None
        
        prompt = self._build_unified_prompt(context)
        if not prompt:
            return None
        
        try:
            cfg = BrainConfig.from_env()
            response = client.chat.completions.create(
                model=cfg.openai_model,
                messages=[
                    {"role": "system", "content": self._get_unified_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=max(0.0, min(1.0, cfg.llm_temperature)) or 0.3,
                max_tokens=cfg.llm_max_tokens or 300,
            )
            
            return response.choices[0].message.content.strip()
        except Exception:
            return None
    
    @log_data_flow("nlg.generate_unified_response_streaming")
    def generate_unified_response_streaming(self, context: NLGContext):
        """Generate streaming response using LLM."""
        client = get_openai_client()
        if not client:
            yield "LLM unavailable. Please try again later."
            return
        
        prompt = self._build_unified_prompt(context)
        if not prompt:
            yield "I couldn't generate a response for your query."
            return
        
        try:
            cfg = BrainConfig.from_env()
            stream = client.chat.completions.create(
                model=cfg.openai_model,
                messages=[
                    {"role": "system", "content": self._get_unified_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=max(0.0, min(1.0, cfg.llm_temperature)) or 0.3,
                max_tokens=cfg.llm_max_tokens or 300,
                stream=True  # Enable streaming
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"I encountered an issue while processing your request: {str(e)}"
    
    @log_call("nlg._build_prompt")
    def _build_prompt(self, context: NLGContext) -> str:
        """Build LLM prompt based on query type and context."""
        role_context = self._get_role_context(context.user_role)
        data_str = self._format_data_for_prompt(context.data_summary)
        
        if context.tool_name == "rbac_blocked":
            return self._build_rbac_prompt(context, role_context, data_str)
        elif context.tool_name == "error":
            return self._build_error_prompt(context, role_context, data_str)
        elif context.tool_name == "no_data":
            return self._build_no_data_prompt(context, role_context, data_str)
        elif "overview" in context.user_question.lower() or "portfolio" in context.user_question.lower():
            return self._build_overview_prompt(context, role_context, data_str)
        elif "top" in context.user_question.lower() or "ranking" in context.tool_name:
            return self._build_ranking_prompt(context, role_context, data_str)
        elif "aggregate" in context.tool_name:
            return self._build_aggregate_prompt(context, role_context, data_str)
        elif context.data_summary.get("total", 0) > 10:
            return self._build_large_dataset_prompt(context, role_context, data_str)
        else:
            return self._build_general_prompt(context, role_context, data_str)
    
    @log_call("nlg._build_overview_prompt")
    def _build_overview_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        return f"""
Provide a portfolio overview based on this data for a {role_context}.

User asked: "{context.user_question}"
Tool used: {context.tool_name} with args: {json.dumps(context.tool_args)}

Data summary:
{data_str}

Generate a 2-3 sentence executive summary highlighting:
1. Overall status/health
2. Key metrics or concerning areas
3. Notable patterns or recommendations

Be specific with numbers and actionable.
"""
    
    @log_call("nlg._build_ranking_prompt")
    def _build_ranking_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        return f"""
Analyze this ranking/performance data for a {role_context}.

User asked: "{context.user_question}"

Data summary:
{data_str}

Generate a 2-3 sentence response that:
1. Identifies the top performer(s) with specific metrics
2. Notes any performance gaps or patterns
3. Suggests potential actions or recognition

Focus on actionable insights, not just restating the numbers.
"""
    
    @log_call("nlg._build_aggregate_prompt")
    def _build_aggregate_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        return f"""
Summarize this breakdown/aggregate data for a {role_context}.

User asked: "{context.user_question}"

Data breakdown:
{data_str}

Generate a 2-3 sentence analysis that:
1. Highlights the distribution or key categories
2. Identifies any imbalances or concerning patterns
3. Suggests what this means for operations

Be specific about percentages or ratios where relevant.
"""
    
    @log_call("nlg._build_large_dataset_prompt")
    def _build_large_dataset_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        return f"""
Summarize these results for a {role_context}.

User asked: "{context.user_question}"

Dataset summary:
{data_str}

Generate a concise 2-3 sentence summary that:
1. States the total count and scope
2. Highlights key patterns or notable items
3. Suggests next steps or areas of focus

Don't just restate the count - provide insight.
"""
    
    @log_call("nlg._build_general_prompt")
    def _build_general_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        return f"""
Provide a natural language summary for a {role_context}.

User asked: "{context.user_question}"

Data:
{data_str}

Generate a helpful 1-2 sentence response that directly answers their question with specific details from the data.
"""
    
    @log_call("nlg._get_system_prompt")
    def _get_system_prompt(self) -> str:
        return """You are a data analyst assistant for an operations dashboard. Generate concise, accurate answers from structured data.

Guidelines:
- Answer the user's question directly and precisely.
- Prefer minimal, factual responses for pure count/yes-no queries.
- Include specific numbers and metrics when relevant.
- Do NOT speculate or add opinions beyond the provided data.
- Do NOT introduce unrelated context (e.g., categories when asked for a count).
- Keep responses to 1-2 sentences unless explicitly asked for more.
- Use professional, neutral language.
- Never make up data not provided."""
    
    @log_call("nlg._get_role_context")
    def _get_role_context(self, user_role: str) -> str:
        """Get role-specific context for prompts."""
        role_map = {
            "admin": "senior executive with organization-wide visibility",
            "reviewer": "PMO reviewer managing assigned Executive Orders",
            "executor": "task executor working on specific assignments"
        }
        return role_map.get(user_role.lower(), "user")
    
    @log_call("nlg._format_data_for_prompt")
    def _format_data_for_prompt(self, data_summary: Dict[str, Any]) -> str:
        """Format data summary for LLM consumption."""
        lines = []
        
        # Handle RBAC context first
        if data_summary.get("rbac_blocked", False):
            lines.append("⚠️ RBAC CONTEXT: The user's request was restricted by their role-based permissions. The data shown below is only what they are authorized to see.")
        
        # Handle different data types
        if "total" in data_summary:
            lines.append(f"Total count: {data_summary['total']}")
        
        # Handle items array - this is the key fix!
        if "items" in data_summary and data_summary["items"]:
            items = data_summary["items"]
            data_type = data_summary.get("data_type", "items")
            
            if data_type == "tasks" and items:
                lines.append("Tasks found:")
                for i, task in enumerate(items[:5], 1):
                    title = task.get("title", "Untitled")
                    status = task.get("status", "unknown")
                    category = task.get("category", "uncategorized")
                    lines.append(f"  {i}. {title} (Status: {status}, Category: {category})")
                    
            elif data_type == "task_updates" and items:
                lines.append("Task updates found:")
                for i, update in enumerate(items[:5], 1):
                    task_id = update.get("task_id", "unknown")[:8]
                    status = update.get("status", "unknown")
                    progress = update.get("progress_pct", "N/A")
                    notes = update.get("notes", "")[:50]
                    lines.append(f"  {i}. Task {task_id} - {status} ({progress}% progress)")
                    if notes:
                        lines.append(f"     Notes: {notes}...")
                        
            elif data_type == "executive_orders" and items:
                lines.append("Executive orders found:")
                for i, eo in enumerate(items[:5], 1):
                    title = eo.get("title", "Untitled")
                    status = eo.get("status", "unknown")
                    lines.append(f"  {i}. {title} (Status: {status})")
                    
            elif data_type == "data" and items:
                # Handle generic data (like category breakdowns)
                lines.append("Data breakdown:")
                for i, item in enumerate(items[:5], 1):
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        lines.append(f"  {i}. {item[0]}: {item[1]}")
                    else:
                        lines.append(f"  {i}. {item}")
                        
            elif data_type == "list" and items:
                lines.append("Items found:")
                for i, item in enumerate(items[:5], 1):
                    if isinstance(item, dict):
                        # Try to extract meaningful info from dict
                        if "user_id" in item and "score" in item:
                            # Use enriched user information if available
                            if "user_display" in item:
                                lines.append(f"  {i}. {item['user_display']}: {item['score']} updates")
                            elif "user_name" in item:
                                lines.append(f"  {i}. {item['user_name']}: {item['score']} updates")
                            else:
                                lines.append(f"  {i}. User {item['user_id'][:8]}: {item['score']} updates")
                        elif "group" in item and "metrics" in item:
                            # Use enriched group information if available
                            if "group_display" in item:
                                lines.append(f"  {i}. {item['group_display']}: {item['metrics'].get('count', 0)} items")
                            else:
                                lines.append(f"  {i}. {item['group']}: {item['metrics'].get('count', 0)} items")
                        else:
                            lines.append(f"  {i}. {str(item)[:50]}...")
                    else:
                        lines.append(f"  {i}. {str(item)}")
            
            if data_summary.get("has_more"):
                lines.append("  ... and more items available")
        
        if "breakdown" in data_summary:
            lines.append("Breakdown:")
            for key, value in data_summary["breakdown"].items():
                lines.append(f"  - {key}: {value}")
        
        if "top_items" in data_summary:
            lines.append("Top items:")
            for i, item in enumerate(data_summary["top_items"][:3], 1):
                lines.append(f"  {i}. {item}")
        
        if "key_stats" in data_summary:
            lines.append("Key statistics:")
            for stat, value in data_summary["key_stats"].items():
                lines.append(f"  - {stat}: {value}")
        
        if "time_range" in data_summary:
            lines.append(f"Time period: {data_summary['time_range']}")
        
        return "\n".join(lines) if lines else "No data summary available"
    
    @log_call("nlg._build_unified_prompt")
    def _build_unified_prompt(self, context: NLGContext) -> str:
        """Build comprehensive prompt that handles all response types."""
        role_context = self._get_role_context(context.user_role)
        data_str = self._format_data_for_prompt(context.data_summary)
        
        return f"""You are a helpful assistant for a {role_context} in a task management system.

User asked: "{context.user_question}"
Tool used: {context.tool_name}
Tool arguments: {json.dumps(context.tool_args, indent=2)}

Data retrieved:
{data_str}

Please provide a natural, helpful response that:
1. Directly answers the user's question with SPECIFIC details from the data
2. Is appropriate for their role ({role_context})
3. Uses the actual data provided to give concrete, accurate information
4. Is informative and detailed, not just counts
5. If no data was found, explain why and suggest alternatives
6. If RBAC context indicates restricted access, acknowledge that the results are limited to what they're authorized to see
7. If there was an error, explain it in user-friendly terms

Guidelines:
- Be professional and helpful
- Don't make up information not in the data
- If the data shows 0 results, explain why this might be
- For counts, be precise (e.g., "There are 5 tasks" not "There are several tasks")
- For lists, mention specific items with details (titles, statuses, categories, etc.)
- For searches, show what was actually found with relevant details
- For breakdowns, explain what the categories/statuses mean
- Include specific examples from the data when relevant
- Keep responses focused but comprehensive

Generate your response:"""
    
    @log_call("nlg._get_unified_system_prompt")
    def _get_unified_system_prompt(self) -> str:
        """Get system prompt for unified response generation."""
        return """You are an intelligent assistant for a task management system. You help users understand their data by providing clear, accurate, and helpful responses based on the information provided.

Your role is to:
- Answer questions directly and accurately
- Provide context and insights when helpful
- Be concise but informative
- Handle all types of queries (counts, lists, errors, access restrictions)
- Maintain a professional, helpful tone
- Never make up information not provided in the data

Always base your response on the actual data provided, and if no data is available, explain why and suggest what the user can do instead."""


class DataSummarizer:
    """Create condensed data summaries for LLM consumption."""
    
    @staticmethod
    @log_data_flow("nlg.summarize_task_data")
    def summarize_task_data(tool_result: Dict[str, Any], tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize task data for NLG."""
        summary = {}
        
        if "tasks" in tool_result:
            tasks = tool_result["tasks"]
            summary["total"] = tool_result.get("total", len(tasks))
            
            if tasks:
                # Status breakdown
                statuses = {}
                categories = {}
                overdue_count = 0
                
                for task in tasks:
                    status = task.get("status", "unknown")
                    statuses[status] = statuses.get(status, 0) + 1
                    
                    category = task.get("category", "uncategorized")
                    categories[category] = categories.get(category, 0) + 1
                    
                    # Check if overdue (simplified)
                    if task.get("due_date") and "2024" in task.get("due_date", ""):
                        overdue_count += 1
                
                summary["breakdown"] = statuses
                summary["categories"] = categories
                if overdue_count > 0:
                    summary["key_stats"] = {"overdue_count": overdue_count}
                
                # Sample titles for context
                summary["top_items"] = [t.get("title", "")[:50] + "..." for t in tasks[:3]]
        
        return summary
    
    @staticmethod
    @log_data_flow("nlg.summarize_update_data")
    def summarize_update_data(tool_result: Any, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize task update data for NLG."""
        summary = {}
        
        # Handle ranking results
        if isinstance(tool_result, list) and tool_result and "user_id" in tool_result[0]:
            summary["total"] = len(tool_result)
            summary["breakdown"] = {f"Rank {i+1}": f"{r['count']} updates" for i, r in enumerate(tool_result[:3])}
            summary["key_stats"] = {
                "top_performer": tool_result[0]["count"],
                "participants": len(tool_result)
            }
            return summary
        
        # Handle regular update results
        if isinstance(tool_result, dict) and "updates" in tool_result:
            updates = tool_result["updates"]
            summary["total"] = tool_result.get("total", len(updates))
            
            if updates:
                # Status breakdown
                statuses = {}
                progress_sum = 0
                progress_count = 0
                blockers_count = 0
                risks_count = 0
                
                for update in updates:
                    status = update.get("status", "unknown")
                    statuses[status] = statuses.get(status, 0) + 1
                    
                    if update.get("progress_pct") is not None:
                        progress_sum += update["progress_pct"]
                        progress_count += 1
                    
                    # Note: blockers/risks not in formatted output, but we can infer from args
                    if tool_args.get("has_blockers"):
                        blockers_count += 1
                    if tool_args.get("has_risks"):
                        risks_count += 1
                
                summary["breakdown"] = statuses
                
                key_stats = {}
                if progress_count > 0:
                    key_stats["avg_progress"] = f"{progress_sum / progress_count:.1f}%"
                if blockers_count > 0:
                    key_stats["with_blockers"] = blockers_count
                if risks_count > 0:
                    key_stats["with_risks"] = risks_count
                
                if key_stats:
                    summary["key_stats"] = key_stats
        
        # Add time context from args
        if tool_args.get("date_from") or tool_args.get("date_to"):
            time_parts = []
            if tool_args.get("date_from"):
                time_parts.append(f"from {tool_args['date_from']}")
            if tool_args.get("date_to"):
                time_parts.append(f"to {tool_args['date_to']}")
            summary["time_range"] = " ".join(time_parts)
        
        return summary
    
    @staticmethod
    @log_data_flow("nlg.summarize_aggregate_data")
    def summarize_aggregate_data(tool_result: Any, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize aggregate/breakdown data for NLG."""
        summary = {}
        
        if isinstance(tool_result, dict):
            summary["breakdown"] = tool_result
            summary["total"] = sum(v for v in tool_result.values() if isinstance(v, (int, float)))
            
            # Find dominant category
            if tool_result:
                max_item = max(tool_result.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
                summary["key_stats"] = {
                    "dominant_category": f"{max_item[0]} ({max_item[1]})",
                    "categories_count": len(tool_result)
                }
        elif isinstance(tool_result, list):
            # Handle list-based aggregates: [{"group": X, "metrics": {"count": N}}, ...]
            total_count = 0
            groups = []
            for item in tool_result:
                if isinstance(item, dict):
                    group = item.get("group", "unknown")
                    metrics = item.get("metrics", {})
                    count = int(metrics.get("count", 0)) if isinstance(metrics.get("count"), (int, str)) else 0
                    total_count += count
                    groups.append(f"{group}: {count}")
            
            summary["total"] = total_count
            summary["breakdown"] = {item.get("group", "unknown"): int(item.get("metrics", {}).get("count", 0)) 
                                  for item in tool_result if isinstance(item, dict)}
            if groups:
                summary["key_stats"] = {
                    "groups": groups,
                    "categories_count": len(tool_result)
                }
        
        return summary
    
    @log_call("nlg._build_rbac_prompt")
    def _build_rbac_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        """Build prompt for RBAC blocked messages."""
        return f"""You are responding to a {role_context} who asked: "{context.user_question}"

The user is trying to access data that is outside their role-based permissions. Generate a polite, professional message explaining that their request cannot be fulfilled due to access restrictions.

Guidelines:
- Be respectful and professional
- Explain the limitation clearly but briefly
- Suggest alternative actions they can take within their scope
- Keep it concise (1-2 sentences)

Generate an appropriate response:"""
    
    @log_call("nlg._build_error_prompt")
    def _build_error_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        """Build prompt for error messages."""
        error = context.tool_args.get("error", "Unknown error")
        return f"""You are responding to a {role_context} who asked: "{context.user_question}"

An error occurred while processing their request: {error}

Generate a helpful, professional error message that:
- Acknowledges the error occurred
- Explains what went wrong in user-friendly terms
- Suggests what they can try instead
- Keeps it concise (1-2 sentences)

Generate an appropriate response:"""
    
    @log_call("nlg._build_no_data_prompt")
    def _build_no_data_prompt(self, context: NLGContext, role_context: str, data_str: str) -> str:
        """Build prompt for no data found messages."""
        data_type = context.tool_args.get("data_type", "data")
        return f"""You are responding to a {role_context} who asked: "{context.user_question}"

No {data_type} was found matching their criteria.

Generate a helpful message that:
- Confirms no data was found
- Suggests alternative search criteria or actions
- Keeps it concise (1-2 sentences)

Generate an appropriate response:"""
    
