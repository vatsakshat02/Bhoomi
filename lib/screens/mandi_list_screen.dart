import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'config.dart';

class MandiListScreen extends StatefulWidget {
  @override
  _MandiListScreenState createState() => _MandiListScreenState();
}

class _MandiListScreenState extends State<MandiListScreen> {
  late Future<List<dynamic>> _nearbyMandis;

  @override
  void initState() {
    super.initState();
    _nearbyMandis = _fetchNearbyMandis();
  }

  Future<List<dynamic>> _fetchNearbyMandis() async {
    try {
      Position position = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high);
      return await fetchMandiData(position.latitude, position.longitude);
    } catch (e) {
      print("❌ Error fetching location: $e");
      return [];
    }
  }

  Future<List<dynamic>> fetchMandiData(double latitude, double longitude) async {
    try {
      final url = Uri.parse('$baseUrl/api/mandis'); // Replace with your backend URL
      final response = await http.post(
        url,
        headers: {"Content-Type": "application/json"},
        body: json.encode({"latitude": latitude, "longitude": longitude}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['recommendations'] != null && data['recommendations'] is List) {
          return data['recommendations'];
        } else {
          print("⚠️ Unexpected response format: recommendations is not a list");
          return [];
        }
      } else {
        throw Exception("❌ Failed to load mandi data");
      }
    } catch (e) {
      print("❌ Error fetching mandi data: $e");
      return [];
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Nearby Mandis'),
        backgroundColor: Colors.teal[100],
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _nearbyMandis,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator()); // Show loading indicator
          } else if (snapshot.hasError) {
            return Center(child: Text('❌ Error: ${snapshot.error}'));
          } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
            return const Center(child: Text('⚠️ No mandis found nearby.'));
          } else {
            return ListView.builder(
              itemCount: snapshot.data!.length,
              itemBuilder: (context, index) {
                final mandi = snapshot.data![index];
                final distance = mandi['distance']?.toStringAsFixed(2) ?? 'N/A';
                final price = mandi['price']?.toString() ?? 'No pricing available';

                return Container(
                  margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
                  decoration: BoxDecoration(
                    border: Border.all(color: Colors.black),
                    borderRadius: BorderRadius.circular(10),
                    color: Colors.teal[50],
                  ),
                  child: ListTile(
                    title: Text(mandi['name'] ?? 'Unknown Mandi'),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('📏 Distance: $distance km'),
                        Text('💰 Pricing: $price'),
                      ],
                    ),
                    trailing: const Icon(Icons.store, color: Colors.teal),
                    onTap: () {
                      Navigator.pushNamed(context, '/mandiDetails', arguments: mandi);
                    },
                  ),
                );
              },
            );
          }
        },
      ),
    );
  }
}
