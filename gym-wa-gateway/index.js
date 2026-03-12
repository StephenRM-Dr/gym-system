const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');

const app = express();
app.use(express.json()); // Para que el servidor entienda JSON

// 1. Configuración del Cliente
const client = new Client({
    authStrategy: new LocalAuth(), // Esto guarda la sesión para no escanear el QR siempre
    puppeteer: {
        headless: false, // Cambia a false si quieres ver el navegador abriéndose
        args: []
    }
});

// 2. Generación del Código QR
client.on('qr', (qr) => {
    console.log('ESCANEAME CON TU CELULAR (Configuración -> Dispositivos vinculados):');
    qrcode.generate(qr, { small: true });
});

// 3. Confirmación de Conexión
client.on('ready', () => {
    console.log('¡WhatsApp está listo y conectado!');
});

// 4. Endpoint para enviar mensajes (La puerta para Python)
app.post('/send-message', async (req, res) => {
    const { number, message } = req.body;

    try {
        // 1. Limpiamos el número por si acaso envían "+" o espacios
        const cleanedNumber = number.replace(/\D/g, '');
        const chatId = `${cleanedNumber}@c.us`;

        // 2. Verificamos si el número está registrado en WhatsApp
        const isRegistered = await client.isRegisteredUser(chatId);

        if (isRegistered) {
            await client.sendMessage(chatId, message);
            res.status(200).json({ status: 'Enviado con éxito' });
        } else {
            res.status(400).json({ status: 'Error', message: 'El número no está registrado en WhatsApp' });
        }
    } catch (error) {
        console.error('Detalle del error:', error);
        res.status(500).json({ status: 'Error al enviar', error: error.message });
    }
});
app.get('/test', (req, res) => {
    res.send('El servidor está vivo y escuchando');
});
const PORT = 3000;
app.listen(PORT, () => {
    client.initialize();
    console.log(`Servidor API corriendo en http://localhost:${PORT}`);
});