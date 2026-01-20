# 📝 Update Profile API Documentation

## Overview
This endpoint allows users to update their profile information, specifically their **full name** and **profile picture**. The profile picture must be sent as a **base64 encoded string**.

## Important Restrictions
- ✅ **Can Update:** `full_name`, `profile_pic`
- ❌ **Cannot Update:** `email` (read-only, any attempt will be rejected)
- ❌ **Cannot Update:** `user_type`, `id`, `date_joined` (automatically read-only)

---

## API Endpoint

### Update Profile
**Endpoint:** `PATCH /authentication/profile/`  
**Method:** `PATCH`  
**Authentication:** Required (JWT Bearer Token)

---

## Request Format

### Headers
```http
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

### Request Body (JSON)
```json
{
  "full_name": "John Doe",
  "profile_pic": "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD..."
}
```

### Base64 Image Format
The `profile_pic` field must be a base64 encoded string in the following format:
```
data:image/[format];base64,[base64_data]
```

**Supported formats:**
- `jpeg` or `jpg`
- `png`
- `gif`
- `webp`
- `bmp`

**Example:**
```
data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD...
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUA...
```

---

## Response Format

### Success Response (200 OK)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "user_type": "employer",
  "profile_pic": "https://res.cloudinary.com/your-cloud/image/upload/v1234567890/profile_pics/123e4567-e89b-12d3-a456-426614174000/profile_123e4567-e89b-12d3-a456-426614174000.jpg",
  "date_joined": "2025-01-15T10:30:00Z",
  "has_paid": null,
  "profile_data": {
    "company_name": "Tech Corp",
    "industry": "Software",
    "office_location": "San Francisco",
    "status": "verified"
  }
}
```

### Error Responses

#### 400 Bad Request - Email Update Attempt
```json
{
  "email": ["Email cannot be updated"]
}
```

#### 400 Bad Request - Invalid Base64 Format
```json
{
  "profile_pic": ["Invalid base64 image format. Expected: data:image/[jpeg|png|gif|webp];base64,[data]"]
}
```

#### 400 Bad Request - Invalid Base64 Encoding
```json
{
  "profile_pic": ["Invalid base64 encoding"]
}
```

#### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## Code Examples

### JavaScript/React
```javascript
// Function to convert image file to base64
const convertToBase64 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
  });
};

// Update profile with name and image
const updateProfile = async (fullName, imageFile, jwtToken) => {
  let requestBody = {};
  
  // Add name if provided
  if (fullName) {
    requestBody.full_name = fullName;
  }
  
  // Add image if provided
  if (imageFile) {
    const base64Image = await convertToBase64(imageFile);
    requestBody.profile_pic = base64Image;
  }
  
  try {
    const response = await fetch('/authentication/profile/', {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(JSON.stringify(errorData));
    }
    
    const data = await response.json();
    console.log('Profile updated successfully:', data);
    return data;
  } catch (error) {
    console.error('Failed to update profile:', error);
    throw error;
  }
};

// Usage example
const handleProfileUpdate = async () => {
  const fileInput = document.getElementById('profileImageInput');
  const nameInput = document.getElementById('fullNameInput');
  
  await updateProfile(
    nameInput.value,
    fileInput.files[0],
    'your_jwt_token_here'
  );
};
```

### React Hook Example
```javascript
import { useState } from 'react';

const useProfileUpdate = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const updateProfile = async (fullName, imageFile) => {
    setLoading(true);
    setError(null);

    try {
      const requestBody = { full_name: fullName };

      if (imageFile) {
        const base64 = await new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.readAsDataURL(imageFile);
          reader.onload = () => resolve(reader.result);
          reader.onerror = reject;
        });
        requestBody.profile_pic = base64;
      }

      const response = await fetch('/authentication/profile/', {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(Object.values(errorData).flat().join(', '));
      }

      const data = await response.json();
      setLoading(false);
      return data;
    } catch (err) {
      setError(err.message);
      setLoading(false);
      throw err;
    }
  };

  return { updateProfile, loading, error };
};

// Usage in component
function ProfileEditor() {
  const { updateProfile, loading, error } = useProfileUpdate();
  const [name, setName] = useState('');
  const [image, setImage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const result = await updateProfile(name, image);
      console.log('Profile updated:', result);
      alert('Profile updated successfully!');
    } catch (err) {
      alert(`Failed to update profile: ${err.message}`);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Full Name"
      />
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setImage(e.target.files[0])}
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Updating...' : 'Update Profile'}
      </button>
      {error && <p style={{ color: 'red' }}>{error}</p>}
    </form>
  );
}
```

### Python Requests
```python
import requests
import base64

def update_profile(jwt_token, full_name=None, image_path=None):
    url = "http://localhost:8000/authentication/profile/"
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Content-Type": "application/json"
    }
    
    data = {}
    
    # Add name if provided
    if full_name:
        data['full_name'] = full_name
    
    # Add image if provided
    if image_path:
        with open(image_path, 'rb') as image_file:
            # Read and encode image
            image_bytes = image_file.read()
            base64_encoded = base64.b64encode(image_bytes).decode('utf-8')
            
            # Determine image type from file extension
            if image_path.endswith('.png'):
                image_type = 'png'
            elif image_path.endswith('.jpg') or image_path.endswith('.jpeg'):
                image_type = 'jpeg'
            elif image_path.endswith('.gif'):
                image_type = 'gif'
            else:
                image_type = 'jpeg'  # default
            
            # Create data URL
            data['profile_pic'] = f"data:image/{image_type};base64,{base64_encoded}"
    
    response = requests.patch(url, headers=headers, json=data)
    
    if response.status_code == 200:
        print("Profile updated successfully!")
        return response.json()
    else:
        print(f"Failed to update profile: {response.status_code}")
        print(response.json())
        return None

# Usage
token = "your_jwt_token_here"
result = update_profile(
    jwt_token=token,
    full_name="John Doe",
    image_path="/path/to/profile.jpg"
)
print(result)
```

### cURL
```bash
# Update only name
curl -X PATCH "http://localhost:8000/authentication/profile/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe"
  }'

# Update only profile picture
curl -X PATCH "http://localhost:8000/authentication/profile/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "profile_pic": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }'

# Update both name and profile picture
curl -X PATCH "http://localhost:8000/authentication/profile/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "profile_pic": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }'
```

### Flutter/Dart
```dart
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> updateProfile({
  required String token,
  String? fullName,
  File? imageFile,
}) async {
  final url = Uri.parse('http://localhost:8000/authentication/profile/');
  final headers = {
    'Authorization': 'Bearer $token',
    'Content-Type': 'application/json',
  };

  Map<String, dynamic> body = {};

  // Add name if provided
  if (fullName != null) {
    body['full_name'] = fullName;
  }

  // Add image if provided
  if (imageFile != null) {
    final bytes = await imageFile.readAsBytes();
    final base64Image = base64Encode(bytes);
    final extension = imageFile.path.split('.').last.toLowerCase();
    
    String imageType;
    if (extension == 'png') {
      imageType = 'png';
    } else if (extension == 'jpg' || extension == 'jpeg') {
      imageType = 'jpeg';
    } else if (extension == 'gif') {
      imageType = 'gif';
    } else {
      imageType = 'jpeg';
    }
    
    body['profile_pic'] = 'data:image/$imageType;base64,$base64Image';
  }

  final response = await http.patch(
    url,
    headers: headers,
    body: jsonEncode(body),
  );

  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  } else {
    throw Exception('Failed to update profile: ${response.body}');
  }
}

// Usage
void main() async {
  try {
    final result = await updateProfile(
      token: 'your_jwt_token',
      fullName: 'John Doe',
      imageFile: File('/path/to/image.jpg'),
    );
    print('Profile updated: $result');
  } catch (e) {
    print('Error: $e');
  }
}
```

---

## Image Processing Details

When you upload a profile picture, it will be automatically:
1. ✅ Uploaded to Cloudinary
2. ✅ Stored in folder: `profile_pics/{user_id}/`
3. ✅ **Automatically resized to 500x500 pixels** (face-centered crop)
4. ✅ **Quality optimized** for web delivery
5. ✅ **Format optimized** (auto-converted to best format)
6. ✅ Previous image is **overwritten** (no duplicates)

### Cloudinary Transformations Applied
- **Size:** 500x500 pixels
- **Crop:** Face-centered fill
- **Quality:** Auto-optimized
- **Format:** Auto-selected for best performance

---

## Testing the API

### Using Postman
1. Create a new `PATCH` request
2. URL: `http://localhost:8000/authentication/profile/`
3. Headers:
   - `Authorization`: `Bearer YOUR_JWT_TOKEN`
   - `Content-Type`: `application/json`
4. Body (raw JSON):
```json
{
  "full_name": "Test User",
  "profile_pic": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
}
```

### Quick JavaScript Console Test
```javascript
// Get base64 from file input
const fileInput = document.createElement('input');
fileInput.type = 'file';
fileInput.accept = 'image/*';
fileInput.onchange = async (e) => {
  const file = e.target.files[0];
  const reader = new FileReader();
  reader.onload = async (event) => {
    const base64 = event.target.result;
    
    const response = await fetch('/authentication/profile/', {
      method: 'PATCH',
      headers: {
        'Authorization': 'Bearer YOUR_TOKEN',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        full_name: 'Test User',
        profile_pic: base64
      })
    });
    
    console.log(await response.json());
  };
  reader.readAsDataURL(file);
};
fileInput.click();
```

---

## Common Errors and Solutions

### Error: "Email cannot be updated"
**Cause:** Frontend is trying to send `email` in the request body.  
**Solution:** Remove `email` from the request. Email updates are not allowed.

### Error: "Invalid base64 image format"
**Cause:** The base64 string is not in the correct format.  
**Solution:** Ensure the string starts with `data:image/[format];base64,` followed by the base64 data.

### Error: "Invalid base64 encoding"
**Cause:** The base64 data is corrupted or invalid.  
**Solution:** Re-encode the image and ensure no characters are lost during transmission.

### Error: "Authentication credentials were not provided"
**Cause:** Missing or invalid JWT token.  
**Solution:** Include `Authorization: Bearer YOUR_TOKEN` in the request headers.

---

## Notes
- Both fields (`full_name` and `profile_pic`) are **optional** in the update request
- You can update just the name, just the image, or both at once
- The email field is **permanently read-only** after account creation
- Profile pictures are stored in Cloudinary with automatic optimization
- Old profile pictures are automatically replaced when uploading a new one
