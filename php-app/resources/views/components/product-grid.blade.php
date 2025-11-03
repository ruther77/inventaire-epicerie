<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    @foreach ($products as $product)
        @component('components.product-card', ['product' => $product])
        @endcomponent
    @endforeach
    @if (empty($products))
        <p class="col-span-full text-center text-slate-500">{{ trans('messages.no_products') }}</p>
    @endif
</div>
