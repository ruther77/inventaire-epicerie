<?php

declare(strict_types=1);

namespace Framework\Routing;

use Framework\Http\Response;
use Framework\Support\Container;

final class Route
{
    private string $pattern;

    private mixed $action;

    public function __construct(
        private readonly string $method,
        private readonly string $uri,
        array|callable $action
    ) {
        $this->action = $action;
        $this->pattern = '#^' . preg_replace('#\{([a-zA-Z_][a-zA-Z0-9_-]*)\}#', '(?P<$1>[^/]+)', $uri) . '$#';
    }

    public function matches(string $path): array|false
    {
        if (!preg_match($this->pattern, $path, $matches)) {
            return false;
        }

        $parameters = [];
        foreach ($matches as $key => $value) {
            if (!is_int($key)) {
                $parameters[$key] = $value;
            }
        }

        return $parameters;
    }

    public function run(Container $container, array $parameters): Response
    {
        if (is_callable($this->action)) {
            $result = ($this->action)(...array_values($parameters));
        } elseif (is_array($this->action) && count($this->action) === 2) {
            [$class, $method] = $this->action;
            $controller = $container->get($class) ?? new $class();
            $result = $controller->{$method}(...array_values($parameters));
        } else {
            throw new \RuntimeException('Invalid route action.');
        }

        return $result instanceof Response ? $result : new Response((string) $result);
    }
}
