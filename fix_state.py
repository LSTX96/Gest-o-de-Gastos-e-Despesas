"""Script temporário para aplicar correções no state.py"""

FILE = r"c:\Users\Meu Note\Desktop\ATIVIDADES\rps_passivo\rps_passivo\state.py"

with open(FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Replace lines 31-32 (0-indexed 30-31) with new formatting
new_lines = [
    '    fig.update_layout(\n',
    '        barmode="group", height=340, margin=dict(t=30, l=50, r=10, b=40),\n',
    '        separators=".,",\n',
    '        paper_bgcolor="white",\n',
    '        plot_bgcolor="white",\n',
    '        font={"family": "Inter, sans-serif", "color": "#475569"},\n',
    '        hoverlabel={"bgcolor": "#1E293B", "font": {"color": "white", "family": "Inter, sans-serif"}},\n',
    '        hovermode="x unified",\n',
    '    )\n',
    '    fig.update_xaxes(gridcolor="#E2E8F0", zerolinecolor="#E2E8F0")\n',
    '    fig.update_yaxes(tickprefix="R$ ", tickformat=",.2f", gridcolor="#E2E8F0", zerolinecolor="#E2E8F0")\n',
]

# Lines 31 and 32 (0-indexed 30 and 31) are the old update_layout and update_yaxes lines
lines[30:32] = new_lines

with open(FILE, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Replaced lines 31-32")
# Verify
with open(FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i in range(29, 42):
    print(f"{i+1}: {lines[i]!r}")
