from django.shortcuts import render
from django.http import HttpResponse
from decimal import Decimal, getcontext
from .services.mnemonic_service import generate_mnemonics

getcontext().prec = 60

# 12-word BIP39 = 128 bits of entropy = 2^128 possible unique wallets
TOTAL_POSSIBLE = 2 ** 128
TOTAL_FORMATTED = f"{TOTAL_POSSIBLE:,}"


def index(request):
    return render(request, 'solapp/index.html')


def test_htmx(request):
    return HttpResponse("<p class='text-green-600 font-bold'>HTMX is working!</p>")


def generate_mnemonics_view(request):
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))

        if quantity < 1 or quantity > 100:
            return HttpResponse("<p class='text-red-600 font-bold'>Invalid quantity.</p>")

        try:
            mnemonics = generate_mnemonics(count=quantity)
        except Exception as e:
            return HttpResponse(f"<p class='text-red-600 font-bold'>Error: {str(e)}</p>")

        # --- Session tracking ---
        session_total = request.session.get('total_generated', 0) + quantity
        request.session['total_generated'] = session_total

        # --- Python does ALL the math ---
        percentage = Decimal(session_total) / Decimal(TOTAL_POSSIBLE) * Decimal(100)
        percentage_str = format(percentage, '.38f')

        # --- Mnemonics HTML ---
        mnemonics_html = ""
        for i, mnemonic in enumerate(mnemonics, 1):
            mnemonics_html += f"""
                <div class='border-2 border-black p-4 mb-3'>
                    <div class='flex justify-between items-start mb-2'>
                        <p class='text-xs font-black tracking-widest'>MNEMONIC #{i}</p>
                        <button
                            onclick="copyToClipboard('{mnemonic}', this)"
                            class='text-xs font-black tracking-widest hover:underline cursor-pointer'>
                            COPY
                        </button>
                    </div>
                    <p class='font-mono text-sm text-black break-all'>{mnemonic}</p>
                </div>
            """

        mnemonics_html += """
            <script>
                document.getElementById('download-btn').classList.remove('hidden');
            </script>
        """

        # --- OOB counter chunk — HTMX swaps this into #odds-counter ---
        oob_html = f"""
            <div id="odds-counter" hx-swap-oob="true">
                <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
                    <div class="md:col-span-2">
                        <p class="text-xs font-black tracking-widest text-gray-400 mb-3">TOTAL POSSIBLE WALLETS (2¹²⁸)</p>
                        <p class="font-mono text-sm font-bold text-white break-all leading-relaxed">{TOTAL_FORMATTED}</p>
                    </div>
                    <div>
                        <p class="text-xs font-black tracking-widest text-gray-400 mb-3">GENERATED THIS SESSION</p>
                        <p class="font-mono text-5xl font-black text-white">{session_total:,}</p>
                    </div>
                </div>
                <div>
                    <p class="text-xs font-black tracking-widest text-gray-400 mb-3">YOUR COVERAGE OF THE ADDRESS SPACE</p>
                    <p class="font-mono text-base font-black text-white mb-4">{percentage_str}%</p>
                    <div class="w-full h-1 bg-gray-800">
                        <div class="h-1 bg-white" style="width: 0%"></div>
                    </div>
                    <p class="text-xs text-gray-600 mt-3 tracking-widest">THE BAR IS NOT BROKEN. YOU ARE JUST VERY SMALL.</p>
                </div>
            </div>
        """

        return HttpResponse(mnemonics_html + oob_html)

    return HttpResponse("<p class='text-red-600 font-bold'>INVALID REQUEST</p>")
