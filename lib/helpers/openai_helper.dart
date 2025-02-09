import 'package:http/http.dart' as http;
import 'dart:convert';

class OpenAIHelper {
  static String getOpenAiApiKey() {
    return '';
  }

  static Future<String> getGeneratedResponse(String prompt) async {
    final String apiKey = getOpenAiApiKey();
    final Uri url = Uri.parse('https://api.openai.com/v1/completions');

    try {
      final response = await http.post(
        url,
        headers: {
          'Authorization': 'Bearer $apiKey',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          "model": "gpt-3.5-turbo", 
          "prompt": prompt,
          "max_tokens": 150,
          "temperature": 0.7,
        }),
      );

      if (response.statusCode == 200) {
        var decodedResponse = jsonDecode(response.body);
        return decodedResponse['choices'][0]['text'].trim();
      } else {
        print('Error: ${response.statusCode}');
        print('Response body: ${response.body}');
        throw Exception('Failed to generate response from OpenAI. Status code: ${response.statusCode}');
      }
    } catch (e) {
      print('An error occurred: $e');
      throw Exception('An unexpected error occurred while contacting OpenAI.');
    }
  }
}
