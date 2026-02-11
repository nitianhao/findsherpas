import React from 'react';
import Link from 'next/link';
import { cn } from "@/lib/utils";
import { MoveRight } from 'lucide-react';

interface AuditSelectorProps {
    currentAudit?: 'ux' | 'relevance' | 'analytics';
    className?: string;
}

const AUDITS = [
    {
        id: 'ux',
        name: 'Search UX Audit',
        path: '/services/search-ux-audit',
        pricingAnchor: '/pricing#ux',
        solves: 'Fixes friction in the search interface and filtering experience.',
        when: 'Choose if users abandon searches or filters are underused.',
    },
    {
        id: 'relevance',
        name: 'Search Relevance Audit',
        path: '/services/search-relevance-audit',
        pricingAnchor: '/pricing#relevance',
        solves: 'Optimizes the algorithms ranking your products.',
        when: "Choose if results don't match intent or zero-results are high.",
    },
    {
        id: 'analytics',
        name: 'Search Analytics Audit',
        path: '/services/search-analytics-audit',
        pricingAnchor: '/pricing#analytics',
        solves: 'Builds a reliable data foundation for search decisions.',
        when: 'Choose if you lack clear data on search performance.',
    },
] as const;

export function AuditSelector({ currentAudit, className }: AuditSelectorProps) {
    return (
        <section className={cn("w-full py-20 md:py-32", className)} id="audit-selector">
            <div className="container px-4 md:px-6 mx-auto max-w-6xl">

                {/* Header Section */}
                <div className="mb-20 md:mb-24 max-w-3xl mx-auto">
                    <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-center mb-10 text-foreground">
                        How to choose the right audit
                    </h2>

                    <div className="grid gap-8 md:gap-12 md:grid-cols-3">
                        <div className="flex flex-col items-center text-center space-y-4">
                            <span className="text-lg font-semibold text-primary">Choose UX Audit if...</span>
                            <p className="text-muted-foreground leading-relaxed">The interface feels clunky or customers get lost.</p>
                        </div>
                        <div className="flex flex-col items-center text-center space-y-4">
                            <span className="text-lg font-semibold text-primary">Choose Relevance Audit if...</span>
                            <p className="text-muted-foreground leading-relaxed">The search engine shows the wrong products.</p>
                        </div>
                        <div className="flex flex-col items-center text-center space-y-4">
                            <span className="text-lg font-semibold text-primary">Choose Analytics Audit if...</span>
                            <p className="text-muted-foreground leading-relaxed">You&apos;re flying blind without reliable data.</p>
                        </div>
                    </div>
                </div>

                {/* Comparison Grid via minimal dividers */}
                <div className="grid md:grid-cols-3 gap-0 divide-y md:divide-y-0 md:divide-x divide-border border-t border-b border-border/50">
                    {AUDITS.map((audit) => {
                        const isCurrent = currentAudit === audit.id;

                        return (
                            <div
                                key={audit.id}
                                className={cn(
                                    "p-8 md:p-12 flex flex-col h-full transition-colors relative group",
                                )}
                            >
                                {isCurrent && (
                                    <div className="absolute inset-0 bg-primary/[0.03] -z-10" />
                                )}

                                <div className="mb-8">
                                    <h3 className="text-2xl font-bold text-foreground mb-3 flex items-center gap-3">
                                        {audit.name}
                                        {isCurrent && <span className="text-xs font-medium text-primary uppercase tracking-wider bg-primary/10 py-1 px-2.5 rounded-full">Current</span>}
                                    </h3>
                                    <p className="text-base font-medium text-primary mb-4 leading-relaxed">
                                        {audit.solves}
                                    </p>
                                    <p className="text-base text-muted-foreground leading-relaxed">
                                        {audit.when}
                                    </p>
                                </div>

                                <div className="mt-auto pt-8 flex flex-col gap-4">
                                    {!isCurrent ? (
                                        <Link
                                            href={audit.path}
                                            className="group/link inline-flex items-center text-base font-semibold text-foreground hover:text-primary transition-colors"
                                        >
                                            View full details
                                            <MoveRight className="ml-2 h-4 w-4 transition-transform group-hover/link:translate-x-1" />
                                        </Link>
                                    ) : (
                                        <span className="text-base text-muted-foreground/40 cursor-default font-medium">
                                            Currently viewing details
                                        </span>
                                    )}

                                    <Link
                                        href={audit.pricingAnchor}
                                        className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                                    >
                                        Jump to pricing
                                    </Link>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}
