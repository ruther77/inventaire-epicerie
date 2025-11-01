import PropTypes from 'prop-types';
import clsx from 'clsx';

export function Button({ variant = 'primary', className, ...props }) {
  return (
    <button
      type="button"
      data-variant={variant}
      className={clsx('ds-button', className)}
      {...props}
    />
  );
}

Button.propTypes = {
  variant: PropTypes.string,
  className: PropTypes.string,
};

Button.defaultProps = {
  variant: 'primary',
  className: undefined,
};

export function Badge({ label, variant = 'neutral', className }) {
  if (!label) {
    return null;
  }
  return (
    <span className={clsx('ds-badge', className)} data-variant={variant}>
      {label}
    </span>
  );
}

Badge.propTypes = {
  label: PropTypes.node,
  variant: PropTypes.string,
  className: PropTypes.string,
};

Badge.defaultProps = {
  label: null,
  variant: 'neutral',
  className: undefined,
};

export function Card({ title, description, children, className }) {
  return (
    <article className={clsx('ds-card', className)}>
      {title ? <h3>{title}</h3> : null}
      {description ? <p>{description}</p> : null}
      {children}
    </article>
  );
}

Card.propTypes = {
  title: PropTypes.node,
  description: PropTypes.node,
  children: PropTypes.node,
  className: PropTypes.string,
};

Card.defaultProps = {
  title: null,
  description: null,
  children: null,
  className: undefined,
};

export function Stack({ gap = '1.25rem', className, children }) {
  return (
    <div className={clsx('ds-stack', className)} style={{ '--ds-stack-gap': gap }}>
      {children}
    </div>
  );
}

Stack.propTypes = {
  gap: PropTypes.string,
  className: PropTypes.string,
  children: PropTypes.node,
};

Stack.defaultProps = {
  gap: '1.25rem',
  className: undefined,
  children: null,
};
