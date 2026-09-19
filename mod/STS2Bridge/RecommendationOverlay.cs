using System;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;
using Godot;

namespace STS2_MCP;

public static partial class McpMod
{
    private static Label? _recommendationLabel;
    private static volatile string _recommendation = "Start Showing Your Hand";
    private static bool _overlayStarted;
    private static bool _overlayErrorReported;

    private static void UpdateRecommendationOverlay()
    {
        if (!_overlayStarted)
        {
            _overlayStarted = true;
            var tree = (SceneTree)Engine.GetMainLoop();
            var layer = new CanvasLayer { Layer = 110 };
            tree.Root.AddChild(layer);
            var panel = new PanelContainer { MouseFilter = Control.MouseFilterEnum.Ignore };
            layer.AddChild(panel);
            panel.SetAnchorsPreset(Control.LayoutPreset.CenterTop);
            panel.OffsetLeft = -280;
            panel.OffsetRight = 280;
            panel.OffsetTop = 75;
            panel.OffsetBottom = 140;
            panel.AddThemeStyleboxOverride("panel", new StyleBoxFlat {
                BgColor = new Color(0.07f, 0.10f, 0.08f, 0.94f),
                BorderColor = new Color(0.55f, 0.64f, 0.43f, 0.7f),
                BorderWidthBottom = 1, BorderWidthTop = 1, BorderWidthLeft = 1, BorderWidthRight = 1,
                CornerRadiusTopLeft = 10, CornerRadiusTopRight = 10,
                CornerRadiusBottomLeft = 10, CornerRadiusBottomRight = 10,
                ContentMarginLeft = 18, ContentMarginRight = 18,
                ContentMarginTop = 12, ContentMarginBottom = 12
            });
            _recommendationLabel = new Label {
                Text = _recommendation,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center,
                AutowrapMode = TextServer.AutowrapMode.WordSmart,
                MouseFilter = Control.MouseFilterEnum.Ignore
            };
            _recommendationLabel.AddThemeFontSizeOverride("font_size", 24);
            panel.AddChild(_recommendationLabel);
            _ = Task.Run(PollRecommendation);
        }
        if (_recommendationLabel != null)
            _recommendationLabel.Text = _recommendation;
    }

    private static async Task PollRecommendation()
    {
        // Use an explicit IPv4 loopback socket. A dual-stack socket can become an
        // IPv4-mapped IPv6 address that does not match macOS's localhost sandbox rule.
        using var handler = new SocketsHttpHandler {
            UseProxy = false,
            ConnectCallback = async (_, cancellation) => {
                var socket = new System.Net.Sockets.Socket(
                    System.Net.Sockets.AddressFamily.InterNetwork,
                    System.Net.Sockets.SocketType.Stream, System.Net.Sockets.ProtocolType.Tcp);
                try {
                    await socket.ConnectAsync(new System.Net.IPEndPoint(System.Net.IPAddress.Loopback, 18765), cancellation);
                    return new System.Net.Sockets.NetworkStream(socket, ownsSocket: true);
                } catch { socket.Dispose(); throw; }
            }
        };
        using var client = new System.Net.Http.HttpClient(handler) {
            Timeout = TimeSpan.FromSeconds(2)
        };
        while (true)
        {
            try
            {
                string json = await client.GetStringAsync("http://127.0.0.1:18765/api/status");
                using var document = JsonDocument.Parse(json);
                var root = document.RootElement;
                _recommendation = root.TryGetProperty("action", out var action) && action.ValueKind == JsonValueKind.String
                    ? action.GetString() ?? "Waiting for the game"
                    : root.GetProperty("message").GetString() ?? "Waiting for the game";
            }
            catch (Exception error)
            {
                if (!_overlayErrorReported)
                {
                    GD.PrintErr("[Showing Your Hand] Local overlay connection: " + error);
                    _overlayErrorReported = true;
                }
                _recommendation = "Start Showing Your Hand";
            }
            await Task.Delay(500);
        }
    }
}
