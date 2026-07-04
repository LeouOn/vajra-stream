/**
 * RouteShell — shared layout wrapper for top-level routes.
 *
 * Provides the standard `flex-1 h-full overflow-hidden` outer container
 * that every routable view lives inside. When `title` is supplied it
 * also renders a `<PageHeader>` at the top of the route, so consumers
 * only need to specify title / subtitle / icon / actions once.
 *
 * Replaces the six duplicated `calc(100vh - 176px)` wrappers that
 * previously lived inside `routes/Practice/`, `routes/Operations/`,
 * and `routes/Settings/`.
 *
 * @component
 */
import React from 'react';
import PageHeader, { type PageHeaderProps } from './PageHeader';

export interface RouteShellProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  icon?: React.ReactNode;
  actions?: React.ReactNode;
  /**
   * Override the outer container className. Defaults to the shared
   * `flex-1 h-full overflow-hidden` so a single route consumes the
   * available space without redundant scroll containers.
   */
  className?: string;
  /**
   * Override the inner body className. Defaults to `h-full overflow-y-auto`
   * so route content can scroll independently of the header.
   */
  bodyClassName?: string;
}

export default function RouteShell({
  children,
  title,
  subtitle,
  icon,
  actions,
  className,
  bodyClassName,
}: RouteShellProps): React.ReactElement {
  const outerClass = className ?? 'flex-1 h-full overflow-hidden';
  const innerClass = bodyClassName ?? 'h-full overflow-y-auto';
  const headerProps: PageHeaderProps = { title: title ?? '', subtitle, icon, actions };
  const showHeader = Boolean(title);

  return (
    <div className={outerClass}>
      {showHeader ? (
        <div className="px-4 md:px-6 pt-4 md:pt-6">
          <PageHeader {...headerProps} />
        </div>
      ) : null}
      <div className={innerClass}>{children}</div>
    </div>
  );
}