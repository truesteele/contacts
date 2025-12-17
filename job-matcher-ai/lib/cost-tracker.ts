/**
 * Cost tracking for AI Recruiter Agent
 * Tracks API usage and estimates costs per search session
 */

export interface CostMetrics {
  anthropicCalls: number;
  enrichLayerCalls: number;
  enrichLayerCacheHits: number;
  perplexityCalls: number;
  totalEstimatedCost: number;
}

class CostTracker {
  private metrics: CostMetrics = {
    anthropicCalls: 0,
    enrichLayerCalls: 0,
    enrichLayerCacheHits: 0,
    perplexityCalls: 0,
    totalEstimatedCost: 0,
  };

  // Cost per API call (estimates)
  private costs = {
    anthropicEvaluation: 0.03, // ~3000 tokens at Claude 4.5 Sonnet pricing
    enrichLayerCall: 0.10, // Enrich Layer per-enrichment cost
    perplexityCall: 0.20, // Perplexity research query
  };

  trackAnthropicCall() {
    this.metrics.anthropicCalls++;
    this.recalculateCost();
  }

  trackEnrichLayerCall(wasCacheHit: boolean = false) {
    if (wasCacheHit) {
      this.metrics.enrichLayerCacheHits++;
    } else {
      this.metrics.enrichLayerCalls++;
    }
    this.recalculateCost();
  }

  trackPerplexityCall() {
    this.metrics.perplexityCalls++;
    this.recalculateCost();
  }

  private recalculateCost() {
    this.metrics.totalEstimatedCost =
      this.metrics.anthropicCalls * this.costs.anthropicEvaluation +
      this.metrics.enrichLayerCalls * this.costs.enrichLayerCall +
      this.metrics.perplexityCalls * this.costs.perplexityCall;
  }

  getMetrics(): CostMetrics {
    return { ...this.metrics };
  }

  getSummary(): string {
    const m = this.metrics;
    const cacheHitRate = m.enrichLayerCalls + m.enrichLayerCacheHits > 0
      ? Math.round((m.enrichLayerCacheHits / (m.enrichLayerCalls + m.enrichLayerCacheHits)) * 100)
      : 0;

    return `💰 Search Cost Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Claude Evaluations: ${m.anthropicCalls} ($${(m.anthropicCalls * this.costs.anthropicEvaluation).toFixed(2)})
Enrich Layer: ${m.enrichLayerCalls} calls, ${m.enrichLayerCacheHits} cached ($${(m.enrichLayerCalls * this.costs.enrichLayerCall).toFixed(2)})
  Cache Hit Rate: ${cacheHitRate}%
Perplexity Research: ${m.perplexityCalls} ($${(m.perplexityCalls * this.costs.perplexityCall).toFixed(2)})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Estimated Total: $${m.totalEstimatedCost.toFixed(2)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`;
  }

  reset() {
    this.metrics = {
      anthropicCalls: 0,
      enrichLayerCalls: 0,
      enrichLayerCacheHits: 0,
      perplexityCalls: 0,
      totalEstimatedCost: 0,
    };
  }
}

// Export a singleton instance
export const costTracker = new CostTracker();
