<?php

declare(strict_types=1);

namespace Framework\Routing;

use Framework\Http\Request;
use Framework\Http\Response;
use Framework\Support\Container;

final class Router
{
    /** @var array<string, Route[]> */
    private array $routes = [];

    public function __construct(private Container $container)
    {
    }

    public function get(string $uri, array|callable $action): void
    {
        $this->addRoute('GET', $uri, $action);
    }

    public function post(string $uri, array|callable $action): void
    {
        $this->addRoute('POST', $uri, $action);
    }

    public function addRoute(string $method, string $uri, array|callable $action): void
    {
        $this->routes[$method][] = new Route($method, $uri, $action);
    }

    public function dispatch(Request $request): Response
    {
        $routes = $this->routes[$request->method] ?? [];
        foreach ($routes as $route) {
            if ($parameters = $route->matches($request->path)) {
                return $route->run($this->container, $parameters);
            }
        }

        return new Response(view('errors/404'), 404);
    }
}
